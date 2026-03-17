import { Button, Input, InputNumber, Table } from "antd";
import { PlusOutlined, DeleteOutlined } from "@ant-design/icons";
import type { DeclarationItem } from "../types";

interface Props {
  items: DeclarationItem[];
  onChange: (items: DeclarationItem[]) => void;
  readOnly?: boolean;
}

export default function CargoItemTable({ items, onChange, readOnly }: Props) {
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
      width: 130,
      render: (_: unknown, __: unknown, i: number) => (
        <Input
          value={items[i].hscode}
          onChange={(e) => updateItem(i, "hscode", e.target.value)}
          maxLength={10}
          placeholder="10자리"
          disabled={readOnly}
        />
      ),
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
        scroll={{ x: 900 }}
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
