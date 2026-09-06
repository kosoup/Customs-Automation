import { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import {
  Button,
  Card,
  Col,
  Form,
  Input,
  Row,
  Space,
  Typography,
  message,
} from "antd";
import { ArrowLeftOutlined } from "@ant-design/icons";

import { getSettings, updateSettings, getApiErrorMessage } from "../api/client";

export default function Settings() {
  const navigate = useNavigate();
  const [form] = Form.useForm();

  useEffect(() => {
    getSettings()
      .then((data) => form.setFieldsValue(data))
      .catch((error: unknown) => message.error(getApiErrorMessage(error, "설정 조회 실패")));
  }, [form]);

  async function handleSave() {
    try {
      const values = await form.validateFields();
      await updateSettings(values);
      message.success("저장되었습니다");
    } catch (error: unknown) {
      message.error(getApiErrorMessage(error, "저장 중 오류가 발생했습니다"));
    }
  }

  return (
    <div style={{ padding: 24, maxWidth: 900, margin: "0 auto" }}>
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 24 }}>
        <Typography.Title level={3} style={{ margin: 0 }}>
          회사(신고인) 설정
        </Typography.Title>
        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate("/")}>
          대시보드
        </Button>
      </div>

      <Form form={form} layout="vertical">
        <Card title="신고인 정보" style={{ marginBottom: 16 }}>
          <Row gutter={16}>
            <Col span={8}>
              <Form.Item name="declarant_code" label="신고인부호">
                <Input maxLength={5} placeholder="5자리" />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="declarant_name" label="신고인상호">
                <Input />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="representative_name" label="대표자명">
                <Input />
              </Form.Item>
            </Col>
          </Row>
        </Card>

        <Card title="수출자 정보" style={{ marginBottom: 16 }}>
          <Row gutter={16}>
            <Col span={8}>
              <Form.Item name="exporter_business_number" label="사업자등록번호">
                <Input placeholder="000-00-00000" />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="exporter_customs_id" label="통관고유부호">
                <Input placeholder="최대 15자리" />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="exporter_postcode" label="우편번호">
                <Input maxLength={10} />
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={16}>
            <Col span={24}>
              <Form.Item name="exporter_address" label="수출자주소">
                <Input />
              </Form.Item>
            </Col>
          </Row>
        </Card>

        <Card title="기본 운송 정보" style={{ marginBottom: 24 }}>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="loading_port" label="적재항 코드">
                <Input placeholder="예: KRPUS (부산항)" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="customs_office" label="신고세관 코드">
                <Input placeholder="예: 010 (서울세관)" />
              </Form.Item>
            </Col>
          </Row>
        </Card>

        <Space>
          <Button type="primary" onClick={handleSave}>
            저장
          </Button>
          <Button onClick={() => navigate("/")}>취소</Button>
        </Space>
      </Form>
    </div>
  );
}
