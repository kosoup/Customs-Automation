import { useRef, useState } from "react";
import { AutoComplete, Button, Input, InputNumber, Table, Tag, Tooltip } from "antd";
import { PlusOutlined, DeleteOutlined, ExclamationCircleOutlined } from "@ant-design/icons";
import type { DeclarationItem } from "../types";
import { checkCustomsConfirmation, getTariff, searchHsCode } from "../api/client";

interface Props {
  items: DeclarationItem[];
  onChange: (items: DeclarationItem[]) => void;
  readOnly?: boolean;
}

interface HsState {
  tariffRate: string | null;
  isCustomsTarget: boolean;
}

export default function CargoItemTable({ items, onChange, readOnly }: Props) {
  const [hsOptions, setHsOptions] = useState<Record<number, { value: string; label: string }[]>>({});
  const [hsInfo, setHsInfo] = useState<Record<number, HsState>>({});
  const debounceTimers = useRef<Record<number, ReturnType<typeof setTimeout>>>({});

  const addItem = () => {
    onChange([
      ...items,
      { item_seq: items.length + 1, quantity: 0, unit_price: 0, amount: 0 },
    ]);
  };

  const removeItem = (index: number) => {
    const next = items
      .filter((_, i) => i !== index)
      .map((item, i) => ({ ...item, item_seq: i + 1 }));
    onChange(next);
  };

  const updateItem = (
    index: number,
    field: keyof DeclarationItem,
    value: unknown
  ) => {
    const next = items.map((item, i) => {
      if (i !== index) return item;
      const updated = { ...item, [field]: value };
      if (field === "quantity" || field === "unit_price") {
        updated.amount =
          (Number(updated.quantity) || 0) * (Number(updated.unit_price) || 0);
      }
      return updated;
    });
    onChange(next);
  };

  const handleHsSearch = (index: number, value: string) => {
    updateItem(index, "hscode", value);
    if (debounceTimers.current[index]) {
      clearTimeout(debounceTimers.current[index]);
    }
    if (!value || value.length < 2) {
      setHsOptions((prev) => ({ ...prev, [index]: [] }));
      return;
    }
    debounceTimers.current[index] = setTimeout(async () => {
      try {
        const result = await searchHsCode(value);
        const options = (result.items || []).map((item) => ({
          value: item.hscode,
          label: `${item.hscode}${item.name_ko ? ` - ${item.name_ko}` : ""}`,
        }));
        setHsOptions((prev) => ({ ...prev, [index]: options }));
      } catch {
        // 검색 실패 무시
      }
    }, 300);
  };

  const handleHsSelect = async (index: number, hscode: string, name_ko?: string) => {
    updateItem(index, "hscode", hscode);
    if (name_ko && !items[index].product_name_ko) {
      updateItem(index, "product_name_ko", name_ko);
    }
    setHsOptions((prev) => ({ ...prev, [index]: [] }));

    // 관세율 + 세관장확인 병렬 조회
    const [tariffRes, checkRes] = await Promise.allSettled([
      getTariff(hscode),
      checkCustomsConfirmation(hscode),
    ]);

    setHsInfo((prev) => ({
      ...prev,
      [index]: {
        tariffRate:
          tariffRes.status === "fulfilled" && tariffRes.value.tariff_rate
            ? tariffRes.value.tariff_rate
            : null,
        isCustomsTarget:
          checkRes.status === "fulfilled" ? checkRes.value.is_target : false,
      },
    }));
  };

  const columns = [
    { title: "란", dataIndex: "item_seq", width: 50 },
    {
      title: "품명(한글)",
      dataIndex: "product_name_ko",
      render: (_: unknown, __: unknown, i: number) => (
        <Input
          value={items[i].product_name_ko}
          onChange={(e) => updateItem(i, "product_name_ko", e.target.value)}
          disabled={readOnly}
        />
      ),
    },
    {
      title: "품명(영문)",
      dataIndex: "product_name_en",
      render: (_: unknown, __: unknown, i: number) => (
        <Input
          value={items[i].product_name_en}
          onChange={(e) => updateItem(i, "product_name_en", e.target.value)}
          disabled={readOnly}
        />
      ),
    },
    {
      title: "HS코드",
      dataIndex: "hscode",
      width: 180,
      render: (_: unknown, __: unknown, i: number) => {
        const info = hsInfo[i];
        return (
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: 4 }}>
              {readOnly ? (
                <Input value={items[i].hscode} disabled style={{ flex: 1 }} />
              ) : (
                <AutoComplete
                  value={items[i].hscode}
                  options={hsOptions[i] || []}
                  onSearch={(v) => handleHsSearch(i, v)}
                  onSelect={(v, opt) => {
                    const name_ko = opt.label.includes(" - ")
                      ? opt.label.split(" - ").slice(1).join(" - ")
                      : undefined;
                    handleHsSelect(i, v, name_ko);
                  }}
                  onChange={(v) => updateItem(i, "hscode", v)}
                  style={{ flex: 1 }}
                >
                  <Input maxLength={10} placeholder="10자리 또는 품목명" />
                </AutoComplete>
              )}
              {info?.isCustomsTarget && (
                <Tooltip title="세관장확인대상 품목입니다">
                  <ExclamationCircleOutlined style={{ color: "#ff4d4f" }} />
                </Tooltip>
              )}
            </div>
            {info?.tariffRate && (
              <div style={{ fontSize: 11, color: "#888", marginTop: 2 }}>
                관세율: <Tag color="blue" style={{ fontSize: 10, padding: "0 4px" }}>{info.tariffRate}%</Tag>
              </div>
            )}
          </div>
        );
      },
    },
    {
      title: "규격",
      dataIndex: "model_spec",
      render: (_: unknown, __: unknown, i: number) => (
        <Input
          value={items[i].model_spec}
          onChange={(e) => updateItem(i, "model_spec", e.target.value)}
          disabled={readOnly}
        />
      ),
    },
    {
      title: "수량",
      dataIndex: "quantity",
      width: 100,
      render: (_: unknown, __: unknown, i: number) => (
        <InputNumber
          value={items[i].quantity}
          onChange={(v) => updateItem(i, "quantity", v)}
          min={0}
          disabled={readOnly}
          style={{ width: "100%" }}
        />
      ),
    },
    {
      title: "단위",
      dataIndex: "unit",
      width: 70,
      render: (_: unknown, __: unknown, i: number) => (
        <Input
          value={items[i].unit}
          onChange={(e) => updateItem(i, "unit", e.target.value)}
          placeholder="EA"
          disabled={readOnly}
        />
      ),
    },
    {
      title: "단가",
      dataIndex: "unit_price",
      width: 120,
      render: (_: unknown, __: unknown, i: number) => (
        <InputNumber
          value={items[i].unit_price}
          onChange={(v) => updateItem(i, "unit_price", v)}
          min={0}
          step={0.01}
          disabled={readOnly}
          style={{ width: "100%" }}
        />
      ),
    },
    {
      title: "금액",
      dataIndex: "amount",
      width: 120,
      render: (_: unknown, __: unknown, i: number) => (
        <InputNumber
          value={items[i].amount}
          disabled
          style={{ width: "100%" }}
        />
      ),
    },
    ...(!readOnly
      ? [
          {
            title: "",
            width: 40,
            render: (_: unknown, __: unknown, i: number) => (
              <Button
                type="text"
                danger
                icon={<DeleteOutlined />}
                onClick={() => removeItem(i)}
              />
            ),
          },
        ]
      : []),
  ];

  return (
    <div>
      <Table
        dataSource={items}
        columns={columns}
        rowKey="item_seq"
        pagination={false}
        size="small"
        scroll={{ x: 1000 }}
      />
      {!readOnly && (
        <Button
          type="dashed"
          onClick={addItem}
          icon={<PlusOutlined />}
          style={{ width: "100%", marginTop: 8 }}
        >
          품목 추가
        </Button>
      )}
    </div>
  );
}
