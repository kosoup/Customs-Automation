import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Card,
  Col,
  Row,
  Statistic,
  Table,
  Tag,
  Button,
  Typography,
  Space,
} from "antd";
import {
  FileTextOutlined,
  CheckCircleOutlined,
  SendOutlined,
  TrophyOutlined,
  UploadOutlined,
  PlusOutlined,
  SettingOutlined,
} from "@ant-design/icons";
import dayjs from "dayjs";

import { getStats, listDeclarations } from "../api/client";
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

export default function Dashboard() {
  const navigate = useNavigate();
  const [stats, setStats] = useState<Record<string, number>>({});
  const [recent, setRecent] = useState<DeclarationListItem[]>([]);

  useEffect(() => {
    getStats().then(setStats);
    listDeclarations(undefined, 1).then((d) => setRecent(d.slice(0, 5)));
  }, []);

  const statCards = [
    { label: "전체", key: "total", icon: <FileTextOutlined />, color: "#1677ff" },
    { label: "검증완료", key: "validated", icon: <CheckCircleOutlined />, color: "#0958d9" },
    { label: "제출됨", key: "submitted", icon: <SendOutlined />, color: "#d46b08" },
    { label: "수리", key: "accepted", icon: <TrophyOutlined />, color: "#389e0d" },
  ];

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
  ];

  return (
    <div style={{ padding: 24, maxWidth: 1200, margin: "0 auto" }}>
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 24 }}>
        <Typography.Title level={3} style={{ margin: 0 }}>
          수출통관 자동화 대시보드
        </Typography.Title>
        <Space>
          <Button icon={<SettingOutlined />} onClick={() => navigate("/settings")}>
            회사 설정
          </Button>
          <Button icon={<UploadOutlined />} onClick={() => navigate("/invoices/upload")}>
            인보이스 업로드
          </Button>
          <Button type="primary" icon={<PlusOutlined />} onClick={() => navigate("/declarations/new")}>
            새 신고서
          </Button>
        </Space>
      </div>

      {/* 통계 카드 */}
      <Row gutter={16} style={{ marginBottom: 24 }}>
        {statCards.map(({ label, key, icon, color }) => (
          <Col span={6} key={key}>
            <Card>
              <Statistic
                title={label}
                value={stats[key] ?? 0}
                prefix={<span style={{ color }}>{icon}</span>}
                valueStyle={{ color }}
              />
            </Card>
          </Col>
        ))}
      </Row>

      {/* 최근 신고서 */}
      <Card
        title="최근 신고서"
        extra={
          <Button type="link" onClick={() => navigate("/")}>
            전체 목록 →
          </Button>
        }
      >
        <Table
          dataSource={recent}
          columns={columns}
          rowKey="id"
          pagination={false}
          size="small"
          onRow={(r) => ({
            onClick: () => navigate(`/declarations/${r.id}`),
            style: { cursor: "pointer" },
          })}
        />
      </Card>
    </div>
  );
}
