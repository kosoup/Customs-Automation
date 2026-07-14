import { useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Card,
  Upload,
  Button,
  Select,
  message,
  Alert,
  Descriptions,
  Spin,
  Space,
} from "antd";
import {
  InboxOutlined,
  ArrowLeftOutlined,
  FileSearchOutlined,
} from "@ant-design/icons";
import type { UploadFile, UploadProps } from "antd";

import {
  getApiErrorMessage,
  uploadInvoice,
} from "../api/client";
import type { InvoiceUploadResult } from "../api/client";

const { Dragger } = Upload;

const TEMPLATES = [
  { value: "", label: "기본 (자동 탐지)" },
  { value: "default", label: "Default" },
];

export default function InvoiceUpload() {
  const navigate = useNavigate();
  const [fileList, setFileList] = useState<UploadFile[]>([]);
  const [template, setTemplate] = useState<string>("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<InvoiceUploadResult | null>(null);
  const [error, setError] = useState<string>("");

  const uploadProps: UploadProps = {
    accept: ".pdf,.xlsx",
    fileList,
    beforeUpload: (file) => {
      setFileList([file as unknown as UploadFile]);
      setResult(null);
      setError("");
      return false; // 자동 업로드 방지
    },
    onRemove: () => {
      setFileList([]);
      setResult(null);
    },
    maxCount: 1,
  };

  const handleUpload = async () => {
    if (fileList.length === 0) {
      message.warning("파일을 선택해주세요");
      return;
    }
    setLoading(true);
    setError("");
    try {
      const file = fileList[0] as unknown as File;
      const res = await uploadInvoice(file, template || undefined);
      setResult(res);
      message.success("파싱 완료! 신고서 초안이 생성되었습니다.");
    } catch (error: unknown) {
      const msg = getApiErrorMessage(error, "업로드/파싱 실패");
      setError(msg);
      message.error(msg);
    } finally {
      setLoading(false);
    }
  };

  const parsed = result?.parsed_data;

  return (
    <div style={{ padding: 24, maxWidth: 900, margin: "0 auto" }}>
      <Space style={{ marginBottom: 16 }}>
        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate("/")}>
          목록
        </Button>
      </Space>

      <Card title="인보이스 업로드" style={{ marginBottom: 16 }}>
        <Dragger {...uploadProps} style={{ marginBottom: 16 }}>
          <p className="ant-upload-drag-icon">
            <InboxOutlined />
          </p>
          <p className="ant-upload-text">
            클릭하거나 파일을 여기에 끌어다 놓으세요
          </p>
          <p className="ant-upload-hint">PDF, Excel (.xlsx) 파일 지원</p>
        </Dragger>

        <Space style={{ marginBottom: 16 }}>
          <span>파싱 템플릿:</span>
          <Select
            value={template}
            onChange={setTemplate}
            options={TEMPLATES}
            style={{ width: 200 }}
          />
          <Button
            type="primary"
            icon={<FileSearchOutlined />}
            onClick={handleUpload}
            loading={loading}
            disabled={fileList.length === 0}
          >
            파싱 시작
          </Button>
        </Space>

        {error && (
          <Alert type="error" message={error} showIcon style={{ marginTop: 8 }} />
        )}
      </Card>

      {loading && (
        <div style={{ textAlign: "center", padding: 40 }}>
          <Spin size="large" tip="파싱 중..." />
        </div>
      )}

      {result && parsed && (
        <Card
          title="파싱 결과 미리보기"
          extra={
            <Button
              type="primary"
              onClick={() => navigate(`/declarations/${result.declaration_id}`)}
            >
              신고서 편집하기 →
            </Button>
          }
        >
          <Descriptions column={2} bordered size="small">
            <Descriptions.Item label="수출자">
              {parsed.exporter_name || "-"}
            </Descriptions.Item>
            <Descriptions.Item label="구매자">
              {parsed.buyer_name || "-"}
            </Descriptions.Item>
            <Descriptions.Item label="인보이스 번호">
              {parsed.invoice_number || "-"}
            </Descriptions.Item>
            <Descriptions.Item label="인보이스 일자">
              {parsed.invoice_date || "-"}
            </Descriptions.Item>
            <Descriptions.Item label="인코텀스">
              {parsed.incoterms || "-"}
            </Descriptions.Item>
            <Descriptions.Item label="통화">
              {parsed.currency_code || "-"}
            </Descriptions.Item>
            <Descriptions.Item label="총금액">
              {parsed.total_amount != null
                ? `${parsed.currency_code || ""} ${Number(parsed.total_amount).toLocaleString()}`
                : "-"}
            </Descriptions.Item>
            <Descriptions.Item label="신고서 ID">
              {result.declaration_id}
            </Descriptions.Item>
          </Descriptions>
        </Card>
      )}
    </div>
  );
}
