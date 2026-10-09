"""
공인인증서 전자서명 서비스
FastAPI ↔ Java 서명 모듈 브릿지

흐름:
  [FastAPI] --HTTP--> [Java SignerService (localhost:8081)]
                            ↓
                    PKCS#12 인증서 로드
                    SEED/ARIA 복호화
                    XML-DSig / PKCS#7 서명
                            ↓
                    서명된 XML 반환
"""
import httpx
import subprocess
import logging
import os
import base64
from pathlib import Path
from typing import Optional, Tuple
from app.models.declaration import SignRequest, SignResponse
from app.core.config import settings

logger = logging.getLogger(__name__)

JAVA_SIGNER_URL = f"http://localhost:{settings.JAVA_SIGNER_PORT}"


# ── Java 서비스 헬스체크 ─────────────────────────────────────────────────────

async def is_signer_available() -> bool:
    """Java 서명 서비스 가동 여부 확인"""
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get(f"{JAVA_SIGNER_URL}/health")
            return resp.status_code == 200
    except Exception:
        return False


# ── Python 폴백 서명 (RSA 전용, SEED 불필요 인증서에만 적용 가능) ─────────────

def _sign_xml_python_fallback(xml_bytes: bytes, cert_path: str, cert_password: str) -> Tuple[bool, Optional[bytes], Optional[str]]:
    """
    Python cryptography 라이브러리를 이용한 기본 RSA 서명
    ⚠ SEED 암호화된 한국 공인인증서는 지원 불가 → Java 모듈 필요
    """
    try:
        from cryptography.hazmat.primitives.serialization import pkcs12
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.asymmetric import padding as asym_padding
        from lxml import etree

        with open(cert_path, "rb") as f:
            p12_data = f.read()

        # PKCS#12 로드 (RSA 인증서만)
        private_key, certificate, _ = pkcs12.load_key_and_certificates(
            p12_data, cert_password.encode("utf-8")
        )

        if private_key is None:
            return False, None, "인증서에서 개인키를 추출할 수 없습니다."

        # XML에 서명 (단순 데이터 서명, 실제 XML-DSig 구조는 Java에서 처리)
        signature = private_key.sign(xml_bytes, asym_padding.PKCS1v15(), hashes.SHA256())
        sig_b64 = base64.b64encode(signature).decode()

        root = etree.fromstring(xml_bytes)
        sig_el = etree.SubElement(
            root,
            "Signature",
            attrib={"Algorithm": "RSA-SHA256", "Value": sig_b64}
        )
        signed_xml = etree.tostring(root, pretty_print=True, xml_declaration=True, encoding="UTF-8")

        logger.info("Python RSA 서명 완료 (폴백 모드)")
        return True, signed_xml, None

    except Exception as e:
        logger.error(f"Python 서명 실패: {e}")
        return False, None, str(e)


# ── Java 서명 서비스 호출 ────────────────────────────────────────────────────

async def sign_xml_via_java(req: SignRequest) -> SignResponse:
    """
    Java 서명 마이크로서비스에 XML 전달 → 서명된 XML 수신

    Java 서비스가 없는 경우 Python 폴백 시도
    """
    if settings.MOCK_MODE:
        logger.info("[MOCK] 서명 생략 (Mock 모드)")
        return SignResponse(success=True, signed_xml=req.xml_content)

    # Java 서비스 가용 여부 확인
    if not await is_signer_available():
        logger.warning("Java 서명 서비스 미가동 → Python 폴백 시도")

        cert_path = req.keystore_path
        if not os.path.exists(cert_path):
            return SignResponse(
                success=False,
                error=f"인증서 파일 없음: {cert_path}\nJava 서명 서비스를 시작하거나 인증서 경로를 확인하세요."
            )

        ok, signed, err = _sign_xml_python_fallback(
            req.xml_content.encode("utf-8"),
            cert_path,
            req.keystore_password
        )
        if ok:
            return SignResponse(success=True, signed_xml=signed.decode("utf-8"))
        else:
            return SignResponse(success=False, error=f"Python 폴백 서명 실패: {err}")

    # Java 서비스 호출
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                f"{JAVA_SIGNER_URL}/sign",
                json={
                    "xmlContent":      req.xml_content,
                    "certAlias":       req.cert_alias,
                    "keystorePath":    req.keystore_path,
                    "keystorePassword": req.keystore_password,
                },
            )
            data = response.json()
            if data.get("success"):
                logger.info("Java 서명 완료")
                return SignResponse(success=True, signed_xml=data["signedXml"])
            else:
                return SignResponse(success=False, error=data.get("error", "Java 서명 실패"))

    except Exception as e:
        logger.error(f"Java 서명 서비스 호출 오류: {e}")
        return SignResponse(success=False, error=str(e))


# ── Java 서명 서비스 프로세스 관리 ───────────────────────────────────────────

_java_process: Optional[subprocess.Popen] = None

def start_java_signer():
    """Java 서명 서비스 subprocess로 시작"""
    global _java_process
    jar_path = Path(__file__).parent.parent.parent / "java_signer" / "target" / "kcs-signer.jar"
    if not jar_path.exists():
        logger.warning(f"Java 서명 JAR 없음: {jar_path}")
        logger.warning("→ mvn package로 빌드 후 재시도하거나, 외부에서 서비스를 직접 실행하세요.")
        return

    try:
        _java_process = subprocess.Popen(
            ["java", "-jar", str(jar_path), f"--server.port={settings.JAVA_SIGNER_PORT}"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        logger.info(f"Java 서명 서비스 시작 (PID: {_java_process.pid}, Port: {settings.JAVA_SIGNER_PORT})")
    except FileNotFoundError:
        logger.error("Java 런타임(JRE) 미설치 → java 명령을 사용할 수 없습니다.")
    except Exception as e:
        logger.error(f"Java 서비스 시작 실패: {e}")


def stop_java_signer():
    """Java 서명 서비스 종료"""
    global _java_process
    if _java_process and _java_process.poll() is None:
        _java_process.terminate()
        logger.info("Java 서명 서비스 종료")
