"""Synthetic, local-only vertical demo for the customs review workflow."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory

import httpx
import openpyxl
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.db.session import Base, get_db
from app.main import app


ARTIFACT_NAMES = (
    "GOVCBR830-demo.xml",
    "declaration-demo.csv",
    "declaration-demo.xlsx",
)


@dataclass(frozen=True)
class DemoSummary:
    artifact_names: tuple[str, ...]
    parse_failure_status: int
    parse_failure_removed_upload: bool
    validation_error_fields: tuple[str, ...]


def _emit(event: str, status: str, **details: object) -> None:
    """Print a redaction-safe JSON event for the demo operator."""
    record = {"event": event, "status": status, **details}
    print(json.dumps(record, ensure_ascii=False, sort_keys=True), flush=True)


def _synthetic_invoice_bytes() -> bytes:
    workbook = openpyxl.Workbook()
    worksheet = workbook.active
    worksheet.title = "Synthetic Invoice"

    metadata = (
        ("Seller", "Synthetic Exporter"),
        ("Buyer", "Synthetic Buyer"),
        ("Invoice No", "SYN-DEMO-001"),
        ("Invoice Date", "2026-08-20"),
        ("Incoterms", "FOB"),
        ("Currency", "USD"),
        ("Total Amount", 25.5),
    )
    for row_number, row in enumerate(metadata, start=1):
        worksheet.cell(row=row_number, column=1, value=row[0])
        worksheet.cell(row=row_number, column=2, value=row[1])

    headers = ("Description", "HS Code", "Qty", "Unit", "Unit Price", "Amount")
    for column, header in enumerate(headers, start=1):
        worksheet.cell(row=9, column=column, value=header)

    values = ("Synthetic Widget", "1234567890", 2, "EA", 12.75, 25.5)
    for column, value in enumerate(values, start=1):
        worksheet.cell(row=10, column=column, value=value)

    buffer = io.BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def _review_payload(declaration: dict, *, valid: bool) -> dict:
    editable_fields = (
        "declarant_code",
        "declarant_name",
        "exporter_name",
        "exporter_business_number",
        "exporter_address",
        "buyer_name",
        "buyer_country_code",
        "buyer_address",
        "incoterms",
        "currency_code",
        "payment_method",
        "loading_port",
        "destination_country_code",
        "destination_port",
        "carrier",
        "shipping_date",
        "net_weight_kg",
        "gross_weight_kg",
        "package_type",
        "package_count",
        "invoice_number",
        "invoice_date",
        "total_amount",
    )
    payload = {field: declaration.get(field) for field in editable_fields}
    payload.update(
        {
            "declarant_code": "A1234",
            "declarant_name": "Synthetic Declarant",
            "exporter_business_number": "000-00-00000",
            "exporter_address": "Synthetic export address",
            "buyer_country_code": "US" if valid else "USA",
            "buyer_address": "Synthetic buyer address",
            "destination_country_code": "US",
            "loading_port": "KRPUS",
            "net_weight_kg": 9.5,
            "gross_weight_kg": 10,
            "package_type": "CT",
            "package_count": 1,
            "total_amount": 25.5 if valid else 30,
        }
    )

    payload["items"] = []
    for item in declaration["items"]:
        reviewed_item = {
            key: value
            for key, value in item.items()
            if key not in {"id", "declaration_id"}
        }
        if not valid:
            reviewed_item["hscode"] = "1234"
        payload["items"].append(reviewed_item)
    return payload


def _require_status(response: httpx.Response, expected: int, event: str) -> None:
    if response.status_code != expected:
        _emit(event, "unexpected_response", http_status=response.status_code)
        raise RuntimeError(
            f"{event}: expected HTTP {expected}, received {response.status_code}"
        )


async def _upload_synthetic_invoice(client: httpx.AsyncClient, filename: str) -> int:
    response = await client.post(
        "/api/invoices/upload",
        files={
            "file": (
                filename,
                _synthetic_invoice_bytes(),
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
    )
    _require_status(response, 201, "invoice.upload")
    return int(response.json()["declaration_id"])


async def _run_valid_case(
    client: httpx.AsyncClient,
    output_dir: Path,
) -> tuple[str, ...]:
    declaration_id = await _upload_synthetic_invoice(client, "synthetic-valid.xlsx")
    _emit("invoice.parsed", "passed", item_count=1)

    fetched = await client.get(f"/api/declarations/{declaration_id}")
    _require_status(fetched, 200, "declaration.fetch")
    review = await client.put(
        f"/api/declarations/{declaration_id}",
        json=_review_payload(fetched.json(), valid=True),
    )
    _require_status(review, 200, "declaration.review")
    _emit("declaration.review", "passed", fields_added=10)

    validation = await client.post(f"/api/declarations/{declaration_id}/validate")
    _require_status(validation, 200, "declaration.validate")
    validation_body = validation.json()
    if not validation_body["valid"]:
        _emit(
            "declaration.validate",
            "failed",
            error_count=len(validation_body["errors"]),
        )
        raise RuntimeError("Synthetic valid case did not pass declaration validation")
    _emit("declaration.validate", "passed", error_count=0)

    exports = (
        (
            ARTIFACT_NAMES[0],
            await client.get(f"/api/declarations/{declaration_id}/export-xml"),
        ),
        (
            ARTIFACT_NAMES[1],
            await client.get(
                f"/api/declarations/{declaration_id}/export-file",
                params={"fmt": "csv"},
            ),
        ),
        (
            ARTIFACT_NAMES[2],
            await client.get(
                f"/api/declarations/{declaration_id}/export-file",
                params={"fmt": "xlsx"},
            ),
        ),
    )

    written: list[str] = []
    for artifact_name, response in exports:
        _require_status(response, 200, "artifact.export")
        content = response.content
        (output_dir / artifact_name).write_bytes(content)
        _emit(
            "artifact.written",
            "passed",
            artifact=artifact_name,
            byte_count=len(content),
            sha256=hashlib.sha256(content).hexdigest()[:12],
        )
        written.append(artifact_name)

    return tuple(written)


async def _run_parse_failure_case(
    client: httpx.AsyncClient,
    upload_dir: Path,
) -> tuple[int, bool]:
    before = set(upload_dir.glob("*")) if upload_dir.exists() else set()
    response = await client.post(
        "/api/invoices/upload",
        files={
            "file": (
                "synthetic-broken.xlsx",
                b"not-an-xlsx",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
    )
    after = set(upload_dir.glob("*")) if upload_dir.exists() else set()
    removed = before == after
    expected = response.status_code == 422 and removed
    _emit(
        "invoice.parse_failure",
        "passed" if expected else "failed",
        http_status=response.status_code,
        rejected=True,
        upload_removed=removed,
    )
    if not expected:
        raise RuntimeError("Broken XLSX was not rejected and cleaned up as expected")
    return response.status_code, removed


async def _run_validation_failure_case(
    client: httpx.AsyncClient,
) -> tuple[str, ...]:
    declaration_id = await _upload_synthetic_invoice(client, "synthetic-invalid.xlsx")
    fetched = await client.get(f"/api/declarations/{declaration_id}")
    _require_status(fetched, 200, "invalid_declaration.fetch")
    review = await client.put(
        f"/api/declarations/{declaration_id}",
        json=_review_payload(fetched.json(), valid=False),
    )
    _require_status(review, 200, "invalid_declaration.review")

    validation = await client.post(f"/api/declarations/{declaration_id}/validate")
    _require_status(validation, 200, "invalid_declaration.validate")
    validation_body = validation.json()
    fields = tuple(sorted({error["field"] for error in validation_body["errors"]}))
    expected_fields = {"buyer_country_code", "items[0].hscode", "total_amount"}
    expected = not validation_body["valid"] and expected_fields.issubset(fields)
    for endpoint in ("export-xml", "export-file?fmt=csv", "export-file?fmt=xlsx"):
        blocked = await client.get(f"/api/declarations/{declaration_id}/{endpoint}")
        _require_status(blocked, 400, "invalid_declaration.export_blocked")
    _emit(
        "declaration.validation_failure",
        "passed" if expected else "failed",
        error_count=len(validation_body["errors"]),
        error_fields=list(fields),
        exports_blocked=3,
        outputs_written=False,
    )
    if not expected:
        raise RuntimeError("Invalid declaration did not fail with the expected fields")
    return fields


async def run_demo(output_dir: Path) -> DemoSummary:
    """Run valid and expected-failure flows using only synthetic local data."""
    output_dir.mkdir(parents=True, exist_ok=True)
    temporary_work_dir = TemporaryDirectory(prefix="customs-automation-demo-")
    work_dir = Path(temporary_work_dir.name)
    valid_upload_dir = work_dir / "valid-uploads"
    parse_failure_upload_dir = work_dir / "parse-failure-uploads"
    validation_upload_dir = work_dir / "validation-uploads"

    engine = create_async_engine("sqlite+aiosqlite://", poolclass=StaticPool)
    session_factory = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    async def override_get_db() -> AsyncIterator[AsyncSession]:
        async with session_factory() as session:
            yield session

    original_upload_dir = settings.UPLOAD_DIR
    original_dependency_overrides = app.dependency_overrides.copy()
    app.dependency_overrides[get_db] = override_get_db
    transport = httpx.ASGITransport(app=app)
    _emit("demo.started", "running", scenarios=3, synthetic_data=True)
    try:
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://demo.local",
        ) as client:
            settings.UPLOAD_DIR = str(valid_upload_dir)
            artifact_names = await _run_valid_case(client, output_dir)

            settings.UPLOAD_DIR = str(parse_failure_upload_dir)
            parse_status, parse_removed = await _run_parse_failure_case(
                client,
                parse_failure_upload_dir,
            )

            settings.UPLOAD_DIR = str(validation_upload_dir)
            validation_fields = await _run_validation_failure_case(client)
    finally:
        settings.UPLOAD_DIR = original_upload_dir
        app.dependency_overrides.clear()
        app.dependency_overrides.update(original_dependency_overrides)
        await engine.dispose()
        temporary_work_dir.cleanup()

    _emit(
        "demo.completed",
        "passed",
        artifact_count=len(artifact_names),
        expected_failure_count=2,
    )
    return DemoSummary(
        artifact_names=artifact_names,
        parse_failure_status=parse_status,
        parse_failure_removed_upload=parse_removed,
        validation_error_fields=validation_fields,
    )


def _default_output_dir() -> Path:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return Path(__file__).resolve().parent.parent / ".demo-output" / timestamp


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run the synthetic local Customs Automation demo.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Directory for the three synthetic export artifacts.",
    )
    args = parser.parse_args()
    output_dir = (args.output_dir or _default_output_dir()).resolve()

    import asyncio

    summary = asyncio.run(run_demo(output_dir))
    print(f"Demo artifacts written: {', '.join(summary.artifact_names)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
