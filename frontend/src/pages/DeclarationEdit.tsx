import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import {
  Card,
  Form,
  Input,
  InputNumber,
  DatePicker,
  Select,
  Button,
  Row,
  Col,
  message,
  Alert,
  Space,
  Tag,
} from "antd";
import {
  SaveOutlined,
  CheckCircleOutlined,
  ArrowLeftOutlined,
  SendOutlined,
  DownloadOutlined,
  SearchOutlined,
} from "@ant-design/icons";
import dayjs from "dayjs";

import {
  getDeclaration,
  createDeclaration,
  updateDeclaration,
  validateDeclaration,
  submitDeclaration,
  trackDeclaration,
  exportFileUrl,
} from "../api/client";
import CargoItemTable from "../components/CargoItemTable";
import type { DeclarationItem, ValidationError } from "../types";

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

const INCOTERMS = [
  "EXW", "FCA", "FAS", "FOB", "CFR", "CIF", "CPT", "CIP", "DAP", "DPU", "DDP",
];

export default function DeclarationEdit() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [form] = Form.useForm();
  const [items, setItems] = useState<DeclarationItem[]>([]);
  const [status, setStatus] = useState("draft");
  const [errors, setErrors] = useState<ValidationError[]>([]);
  const [loading, setLoading] = useState(false);
  const isNew = !id;
  const readOnly = !["draft", "validated"].includes(status);

  useEffect(() => {
    if (id) {
      getDeclaration(Number(id)).then((decl) => {
        setStatus(decl.status);
        setItems(decl.items);
        form.setFieldsValue({
          ...decl,
          shipping_date: decl.shipping_date ? dayjs(decl.shipping_date) : null,
          invoice_date: decl.invoice_date ? dayjs(decl.invoice_date) : null,
        });
      });
    }
  }, [id, form]);

  const handleSave = async () => {
    setLoading(true);
    try {
      const values = form.getFieldsValue();
      const body = {
        ...values,
        shipping_date: values.shipping_date?.format("YYYY-MM-DD"),
        invoice_date: values.invoice_date?.format("YYYY-MM-DD"),
        items,
      };

      if (isNew) {
        const created = await createDeclaration(body);
        message.success("저장되었습니다");
        navigate(`/declarations/${created.id}`, { replace: true });
      } else {
        await updateDeclaration(Number(id), body);
        message.success("수정되었습니다");
        setStatus("draft");
        setErrors([]);
      }
    } catch (e: any) {
      message.error(e.response?.data?.detail || "저장 실패");
    } finally {
      setLoading(false);
    }
  };

  const handleValidate = async () => {
    if (isNew) return;
    setLoading(true);
    try {
      const result = await validateDeclaration(Number(id));
      setErrors(result.errors);
      if (result.valid) {
        setStatus("validated");
        message.success("검증 통과");
      } else {
        message.warning(`${result.errors.length}건의 오류가 있습니다`);
      }
    } catch (e: any) {
      message.error("검증 실패");
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async () => {
    if (isNew) return;
    setLoading(true);
    try {
      await submitDeclaration(Number(id), "file_export");
      setStatus("submitted");
      message.success("제출(file_export) 완료. 파일을 다운로드하여 UNI-PASS에 업로드하세요.");
    } catch (e: any) {
      message.error(e.response?.data?.detail || "제출 실패");
    } finally {
      setLoading(false);
    }
  };

  const handleTrack = async () => {
    if (isNew) return;
    setLoading(true);
    try {
      const result = await trackDeclaration(Number(id)) as any;
      if (result.code === "NOT_CONFIGURED") {
        message.warning(result.message);
      } else {
        message.info(
          `상태: ${result.declaration_status || "-"} / 수리번호: ${result.accept_number || "-"}`
        );
      }
    } catch {
      message.error("조회 실패");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ padding: 24, maxWidth: 1200, margin: "0 auto" }}>
      <Space style={{ marginBottom: 16 }}>
        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate("/declarations")}>
          목록
        </Button>
        <Tag color={STATUS_COLORS[status]}>
          {STATUS_LABELS[status] || status}
        </Tag>
      </Space>

      {errors.length > 0 && (
        <Alert
          type="warning"
          showIcon
          style={{ marginBottom: 16 }}
          message="검증 오류"
          description={
            <ul style={{ margin: 0, paddingLeft: 20 }}>
              {errors.map((e, i) => (
                <li key={i}>
                  <strong>{e.field}</strong>: {e.message}
                </li>
              ))}
            </ul>
          }
        />
      )}

      <Form form={form} layout="vertical" disabled={readOnly}>
        {/* 신고인/수출자 */}
        <Card title="신고인 / 수출자" size="small" style={{ marginBottom: 16 }}>
          <Row gutter={16}>
            <Col span={6}>
              <Form.Item label="신고인부호" name="declarant_code">
                <Input maxLength={5} placeholder="5자리" />
              </Form.Item>
            </Col>
            <Col span={6}>
              <Form.Item label="신고인명" name="declarant_name">
                <Input />
              </Form.Item>
            </Col>
            <Col span={6}>
              <Form.Item label="수출자명" name="exporter_name">
                <Input />
              </Form.Item>
            </Col>
            <Col span={6}>
              <Form.Item label="사업자등록번호" name="exporter_business_number">
                <Input placeholder="000-00-00000" />
              </Form.Item>
            </Col>
          </Row>
          <Form.Item label="수출자 주소" name="exporter_address">
            <Input />
          </Form.Item>
        </Card>

        {/* 구매자 */}
        <Card title="구매자" size="small" style={{ marginBottom: 16 }}>
          <Row gutter={16}>
            <Col span={8}>
              <Form.Item label="구매자명" name="buyer_name">
                <Input />
              </Form.Item>
            </Col>
            <Col span={4}>
              <Form.Item label="국가코드" name="buyer_country_code">
                <Input maxLength={2} placeholder="US" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item label="구매자 주소" name="buyer_address">
                <Input />
              </Form.Item>
            </Col>
          </Row>
        </Card>

        {/* 무역조건 */}
        <Card title="무역조건" size="small" style={{ marginBottom: 16 }}>
          <Row gutter={16}>
            <Col span={4}>
              <Form.Item label="인코텀스" name="incoterms">
                <Select allowClear placeholder="선택">
                  {INCOTERMS.map((t) => (
                    <Select.Option key={t} value={t}>
                      {t}
                    </Select.Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
            <Col span={4}>
              <Form.Item label="통화" name="currency_code">
                <Input maxLength={3} placeholder="USD" />
              </Form.Item>
            </Col>
            <Col span={4}>
              <Form.Item label="결제방식" name="payment_method">
                <Input placeholder="T/T" />
              </Form.Item>
            </Col>
            <Col span={6}>
              <Form.Item label="인보이스 번호" name="invoice_number">
                <Input />
              </Form.Item>
            </Col>
            <Col span={6}>
              <Form.Item label="인보이스 일자" name="invoice_date">
                <DatePicker style={{ width: "100%" }} />
              </Form.Item>
            </Col>
          </Row>
        </Card>

        {/* 운송 */}
        <Card title="운송" size="small" style={{ marginBottom: 16 }}>
          <Row gutter={16}>
            <Col span={6}>
              <Form.Item label="적재항" name="loading_port">
                <Input placeholder="KRPUS" />
              </Form.Item>
            </Col>
            <Col span={4}>
              <Form.Item label="목적국" name="destination_country_code">
                <Input maxLength={2} placeholder="US" />
              </Form.Item>
            </Col>
            <Col span={6}>
              <Form.Item label="목적항" name="destination_port">
                <Input placeholder="USLAX" />
              </Form.Item>
            </Col>
            <Col span={4}>
              <Form.Item label="운송사" name="carrier">
                <Input />
              </Form.Item>
            </Col>
            <Col span={4}>
              <Form.Item label="선적일" name="shipping_date">
                <DatePicker style={{ width: "100%" }} />
              </Form.Item>
            </Col>
          </Row>
        </Card>

        {/* 중량/포장 */}
        <Card title="중량 / 포장" size="small" style={{ marginBottom: 16 }}>
          <Row gutter={16}>
            <Col span={5}>
              <Form.Item label="순중량(kg)" name="net_weight_kg">
                <InputNumber min={0} step={0.001} style={{ width: "100%" }} />
              </Form.Item>
            </Col>
            <Col span={5}>
              <Form.Item label="총중량(kg)" name="gross_weight_kg">
                <InputNumber min={0} step={0.001} style={{ width: "100%" }} />
              </Form.Item>
            </Col>
            <Col span={4}>
              <Form.Item label="포장종류" name="package_type">
                <Input placeholder="CT" />
              </Form.Item>
            </Col>
            <Col span={4}>
              <Form.Item label="포장개수" name="package_count">
                <InputNumber min={0} style={{ width: "100%" }} />
              </Form.Item>
            </Col>
            <Col span={6}>
              <Form.Item label="총금액" name="total_amount">
                <InputNumber min={0} step={0.01} style={{ width: "100%" }} />
              </Form.Item>
            </Col>
          </Row>
        </Card>

        {/* 품목 */}
        <Card title="품목 상세" size="small" style={{ marginBottom: 16 }}>
          <CargoItemTable
            items={items}
            onChange={setItems}
            readOnly={readOnly}
          />
        </Card>

        <Space style={{ marginTop: 8 }}>
          {!readOnly && (
            <>
              <Button
                type="primary"
                icon={<SaveOutlined />}
                onClick={handleSave}
                loading={loading}
              >
                저장
              </Button>
              {!isNew && (
                <Button
                  icon={<CheckCircleOutlined />}
                  onClick={handleValidate}
                  loading={loading}
                >
                  검증
                </Button>
              )}
            </>
          )}
          {!isNew && status === "validated" && (
            <Button
              type="primary"
              icon={<SendOutlined />}
              onClick={handleSubmit}
              loading={loading}
            >
              제출 (파일 내보내기)
            </Button>
          )}
          {!isNew && (
            <Button
              icon={<DownloadOutlined />}
              href={exportFileUrl(Number(id))}
              target="_blank"
            >
              Excel 다운로드
            </Button>
          )}
          {!isNew && status === "submitted" && (
            <Button
              icon={<SearchOutlined />}
              onClick={handleTrack}
              loading={loading}
            >
              통관 상태 조회
            </Button>
          )}
        </Space>
      </Form>
    </div>
  );
}
