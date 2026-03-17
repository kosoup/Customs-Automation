import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Table, Button, Tag, Popconfirm, message, Tabs } from "antd";
import { PlusOutlined, DeleteOutlined, UploadOutlined } from "@ant-design/icons";
import dayjs from "dayjs";

import { listDeclarations, deleteDeclaration } from "../api/client";
import type { DeclarationListItem } from "../types";

const STATUS_COLORS: Record<string, string> = {
  draft: "default",
  validated: "blue",
  submitted: "orange",
  accepted: "green",
  rejected: "red",
};

const STATUS_LABELS: Record<string, string> = {
  draft: "초안",
  validated: "검증완료",
  submitted: "제출됨",
  accepted: "수리",
  rejected: "반려",
};

export default function DeclarationList() {
  const navigate = useNavigate();
  const [data, setData] = useState<DeclarationListItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [statusFilter, setStatusFilter] = useState<string | undefined>();

  const fetchData = async () => {
    setLoading(true);
    try {
      const result = await listDeclarations(statusFilter);
      setData(result);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [statusFilter]);

  const handleDelete = async (id: number) => {
    try {
      await deleteDeclaration(id);
      message.success("삭제되었습니다");
      fetchData();
    } catch (e: any) {
      message.error(e.response?.data?.detail || "삭제 실패");
    }
  };

  const columns = [
    { title: "ID", dataIndex: "id", width: 60 },
    {
      title: "상태",
      dataIndex: "status",
      width: 90,
      render: (s: string) => (
        <Tag color={STATUS_COLORS[s]}>{STATUS_LABELS[s] || s}</Tag>
      ),
    },
    { title: "수출자", dataIndex: "exporter_name" },
    { title: "구매자", dataIndex: "buyer_name" },
    { title: "인보이스 번호", dataIndex: "invoice_number" },
    {
      title: "금액",
      render: (_: unknown, r: DeclarationListItem) =>
        r.total_amount != null
          ? `${r.currency_code || ""} ${Number(r.total_amount).toLocaleString()}`
          : "-",
    },
    {
      title: "생성일",
      dataIndex: "created_at",
      render: (d: string) => dayjs(d).format("YYYY-MM-DD HH:mm"),
    },
    {
      title: "",
      width: 50,
      render: (_: unknown, r: DeclarationListItem) =>
        r.status === "draft" ? (
          <Popconfirm title="삭제하시겠습니까?" onConfirm={() => handleDelete(r.id)}>
            <Button type="text" danger icon={<DeleteOutlined />} size="small" />
          </Popconfirm>
        ) : null,
    },
  ];

  const tabs = [
    { key: "", label: "전체" },
    { key: "draft", label: "초안" },
    { key: "validated", label: "검증완료" },
    { key: "submitted", label: "제출됨" },
    { key: "accepted", label: "수리" },
  ];

  return (
    <div style={{ padding: 24, maxWidth: 1200, margin: "0 auto" }}>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          marginBottom: 16,
        }}
      >
        <h2 style={{ margin: 0 }}>수출신고서 목록</h2>
        <div style={{ display: "flex", gap: 8 }}>
          <Button
            icon={<UploadOutlined />}
            onClick={() => navigate("/invoices/upload")}
          >
            인보이스 업로드
          </Button>
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => navigate("/declarations/new")}
          >
            새 신고서
          </Button>
        </div>
      </div>

      <Tabs
        activeKey={statusFilter || ""}
        onChange={(key) => setStatusFilter(key || undefined)}
        items={tabs.map((t) => ({ key: t.key, label: t.label }))}
      />

      <Table
        dataSource={data}
        columns={columns}
        rowKey="id"
        loading={loading}
        onRow={(r) => ({ onClick: () => navigate(`/declarations/${r.id}`), style: { cursor: "pointer" } })}
        size="middle"
      />
    </div>
  );
}
