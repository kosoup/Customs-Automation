import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { Alert, Button, Card, Checkbox, Collapse, Input, Space, Spin, Table, Tag, Typography, message } from 'antd';
import { prepareDocument, getApiErrorMessage } from '../api/client';
import type { PreparationResult, PreparationCell } from '../api/client';

const PROFILE_KEYS = ['환급신청인', '간이자동정액환급여부', '구매자코드', '거래구분'];
const DEMO_PROFILE = { '환급신청인': '2', '간이자동정액환급여부': 'NO', '구매자코드': 'DEMO-BUYER-001', '거래구분': '11' };
function issuesFor(result: PreparationResult | null): string[] {
  if (!result) return [];
  const issues: string[] = [];
  for (const [key, field] of Object.entries(result.common)) {
    if (!field.value.trim()) issues.push(`공통 ${key}: 확인 필요`);
  }
  if (!result.items.length) issues.push('품목 없음: 원문 표 확인 필요');
  let sum = 0; let validAmounts = true;
  result.items.forEach((row, index) => {
    for (const key of ['규격1', '수량', '단가', '금액', '세번부호', '품명', '거래품명', 'FTA발급여부', '원산지', '원산지코드']) {
      if (!row[key]?.value.trim()) issues.push(`${index + 1}행 ${key}: 확인 필요`);
    }
    const values = ['수량', '단가', '금액'].map(key => row[key]?.value.replaceAll(',', '') || '');
    const valid = values.every(v => /^\d+(\.\d+)?$/.test(v));
    if (!valid) issues.push(`${index + 1}행 숫자 판독 확인`);
    else if (Number(values[0]) <= 0 || Math.abs(Number(values[0]) * Number(values[1]) - Number(values[2])) > 0.010001) issues.push(`${index + 1}행 수량×단가와 금액 확인`);
    if (/^\d+(\.\d+)?$/.test(values[2])) sum += Number(values[2]); else validAmounts = false;
    const fta = row['FTA발급여부'].value;
    if (!['Y', 'N'].includes(fta)) issues.push(`${index + 1}행 FTA Y/N 확인`);
    if (fta === 'Y' && !row['FTA발급협정코드'].value) issues.push(`${index + 1}행 FTA 협정코드 필요`);
    if (fta === 'N' && row['FTA발급협정코드'].value) issues.push(`${index + 1}행 FTA N의 코드 칸은 비워야 합니다`);
  });
  for (const key of ['운임비', '기타금액', '총금액', '총중량', '전체순중량', '카톤수']) {
    const value = result.common[key].value.replaceAll(',', '');
    if (value && !/^\d+(\.\d+)?$/.test(value)) issues.push(`공통 ${key}: 숫자 형식 확인`);
  }
  const total = result.common['총금액'].value.replaceAll(',', '');
  if (validAmounts && total && Math.abs(sum - Number(total)) > 0.010001) issues.push('품목 합계와 총금액 불일치');
  return issues;
}
function safeCell(value: string) {
  const clean = value.replace(/[\t\r\n]+/g, ' ');
  return /^[=+\-@]/.test(clean.trimStart()) ? `'${clean}` : clean;
}
export default function Preparation() {
  const [file, setFile] = useState<File | null>(null);
  const [profile, setProfile] = useState<Record<string, string>>({});
  const [result, setResult] = useState<PreparationResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [page, setPage] = useState(1);
  const [selected, setSelected] = useState<PreparationCell | null>(null);
  const [reviewed, setReviewed] = useState(false);
  const [edits, setEdits] = useState<Record<string, { before: string; after: string }>>({});
  const [error, setError] = useState('');
  const [elapsed, setElapsed] = useState(0);
  useEffect(() => {
    if (!busy) return;
    const started = Date.now();
    const timer = window.setInterval(() => setElapsed(Math.floor((Date.now() - started) / 1000)), 1000);
    return () => window.clearInterval(timer);
  }, [busy]);
  const issues = useMemo(() => issuesFor(result), [result]);
  async function loadSample() {
    try {
      const response = await fetch('/demo/synthetic-shipping-scan.pdf');
      if (!response.ok) throw new Error('sample unavailable');
      setFile(new File([await response.blob()], 'synthetic-shipping-scan.pdf', { type: 'application/pdf' }));
      setProfile(DEMO_PROFILE); setResult(null); setSelected(null); setReviewed(false); setEdits({});
    } catch { message.error('합성 PDF를 불러오지 못했습니다. 파일을 직접 선택해 주세요.'); }
  }
  async function run() {
    if (!file) return;
    setBusy(true); setElapsed(0); setError(''); setResult(null); setSelected(null); setReviewed(false); setEdits({});
    try { const data = await prepareDocument(file, profile); setResult(data); setPage(1); }
    catch (err) { setError(getApiErrorMessage(err, '문서를 처리하지 못했습니다.')); }
    finally { setBusy(false); }
  }
  function edit(key: string, value: string, index?: number) {
    if (!result) return;
    const original = index === undefined ? result.common[key] : result.items[index][key];
    const id = index === undefined ? `공통.${key}` : `${index + 1}행.${key}`;
    setEdits(previous => ({ ...previous, [id]: { before: previous[id]?.before ?? original.value, after: value } }));
    const changed = { ...original, value, kind: 'manual' };
    setResult(index === undefined ? { ...result, common: { ...result.common, [key]: changed } } : { ...result, items: result.items.map((row, i) => i === index ? { ...row, [key]: changed } : row) });
    setReviewed(false);
  }
  function evidence(field: PreparationCell) { setSelected(field); if (field.page) setPage(field.page); }
  function addRow() {
    if (!result) return;
    const row = Object.fromEntries(result.columns.map(key => [key, { value: '', page: null, evidence: '사용자가 추가한 행', kind: 'manual' }]));
    setResult({ ...result, items: [...result.items, row] }); setReviewed(false);
  }
  function download() {
    if (!result) return;
    const blob = new Blob([JSON.stringify({ ...result, pages: result.pages.map(p => ({ number: p.number, text: p.text })), reviewed, current_issues: issues, edits, status: 'draft', ecom_verified: false }, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob); const anchor = document.createElement('a'); anchor.href = url; anchor.download = 'declaration-draft.json'; anchor.click(); window.setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
  async function copy() {
    if (!result) return;
    const keys = result.columns.slice(0, 12);
    try { await navigator.clipboard.writeText(result.items.map(row => keys.map(key => safeCell(row[key].value)).join('\t')).join('\n')); message.success('12열 초안을 복사했습니다. ecom 호환은 미검증입니다.'); }
    catch { message.error('클립보드 접근에 실패했습니다. JSON 초안을 저장해 주세요.'); }
  }
  const changedCount = Object.values(edits).filter(edit => edit.before !== edit.after).length;
  return <main style={{ padding: 24, maxWidth: 1600, margin: '0 auto' }}>
    <Link to="/">← 대시보드</Link>
    <Typography.Title level={2}>선적서류 → 신고서 초안</Typography.Title>
    <Typography.Paragraph>이미지 PDF를 읽어 공통사항과 란항목을 작성합니다. 원문과 대조하고 필요한 부분을 수정하세요.</Typography.Paragraph>
    <Alert type="info" showIcon title="가능성 검증용 시제품" description="대표 영문 Invoice·Packing List 양식의 로컬 OCR 및 항목 규칙을 사용합니다. 임의 양식의 정확도와 ecom 자동 입력은 미검증입니다. 관세청 송신 기능은 없습니다. 문서는 처리 후 서버에 보관하지 않으며, 화면을 새로고침하면 초안이 사라집니다." />
    <Card style={{ marginTop: 16 }} title="1. 문서와 기본 설정">
      <Space wrap><Button disabled={busy} onClick={loadSample}>합성 PDF와 설정 불러오기</Button><input aria-label="선적서류 PDF" disabled={busy} type="file" accept="application/pdf,.pdf" onChange={event => { setFile(event.target.files?.[0] ?? null); setResult(null); setReviewed(false); setSelected(null); setEdits({}); }} /><Button type="primary" disabled={!file} loading={busy} onClick={run}>PDF 읽고 전체 초안 작성</Button><span>{file?.name || "PDF · 최대 10MB / 12페이지"}</span></Space>
      <Collapse style={{ marginTop: 12 }} items={[{ key: 'profile', label: 'PDF에 없는 기본 설정 (비워두면 확인 대상으로 표시)', children: <><Space wrap>{PROFILE_KEYS.map(key => <label key={key}>{key}<Input aria-label={`기본 설정 ${key}`} disabled={busy} value={profile[key] || ''} onChange={e => setProfile({ ...profile, [key]: e.target.value })} /></label>)}</Space><p><Button disabled={busy} onClick={() => setProfile(DEMO_PROFILE)}>합성 시연 설정 적용</Button> 실제 거래처 설정이 아닙니다. 설정 변경은 다음 초안 작성에 적용됩니다.</p></> }]} />
    </Card>
    {busy && <div style={{ margin: "16px 0" }}><Spin /> 문서를 읽고 있습니다 · {elapsed}초</div>}
    {error && <Alert style={{ marginTop: 12 }} type="error" title={error} />}
    {result && <>
      <Space wrap style={{ margin: '16px 0' }}><Tag color="blue">공통 {Object.keys(result.common).length}개 · 품목 {result.items.length}행</Tag><Tag>처리 {result.elapsed_seconds}초</Tag><Tag>수정 {changedCount}칸</Tag><Tag color={issues.length ? 'orange' : 'green'}>확인 사항 {issues.length}개</Tag><Tag>{result.engine}</Tag></Space>
      <div style={{ display: 'grid', gridTemplateColumns: 'minmax(280px, 0.85fr) minmax(400px, 1.15fr)', gap: 16, alignItems: 'start', overflowX: 'auto' }}>
        <Card title="2. 원문과 근거" style={{ position: 'sticky', top: 8 }}>
          <Space>{result.pages.map(p => <Button key={p.number} type={page === p.number ? 'primary' : 'default'} onClick={() => setPage(p.number)}>{p.number}페이지</Button>)}</Space>
          {selected && <Alert style={{ marginTop: 12 }} title={selected.page ? `${selected.page}페이지 원문` : '입력 근거'} description={selected.evidence || '추출 근거 없음 — 직접 확인 필요'} type="info" />}
          <img style={{ width: '100%', marginTop: 12 }} src={result.pages.find(p => p.number === page)?.image} alt={`선적서류 원문 ${page}페이지`} />
          <Collapse items={[{ key: 'text', label: 'OCR 원문 텍스트', children: <pre style={{ whiteSpace: 'pre-wrap' }}>{result.pages.find(p => p.number === page)?.text}</pre> }]} />
        </Card>
        <Card title="3. 공통항목 자동 작성 결과">
          <Table pagination={false} size="small" rowKey="key" dataSource={Object.entries(result.common).map(([key, field]) => ({ key, field }))} columns={[
            { title: '항목', dataIndex: 'key', width: 150 },
            { title: '초안 값', render: (_, record) => <Input aria-label={`공통 ${record.key}`} status={!record.field.value ? 'warning' : undefined} value={record.field.value} onChange={e => edit(record.key, e.target.value)} /> },
            { title: '근거', width: 95, render: (_, record) => <Button type="link" onClick={() => evidence(record.field)}>{record.field.kind === 'profile' ? '설정값' : record.field.kind === 'manual' ? '수정됨' : record.field.page ? `${record.field.page}쪽` : '미확인'}</Button> },
          ]} />
        </Card>
      </div>
      <Card style={{ marginTop: 16 }} title="4. 란항목 자동 작성 결과 · 셀을 선택하면 근거 페이지로 이동" extra={<Button onClick={addRow}>누락 품목 행 추가</Button>}>
        <Table scroll={{ x: 2200 }} pagination={false} size="small" rowKey="index" dataSource={result.items.map((row, index) => ({ row, index }))} columns={[
          { title: '행', width: 55, fixed: 'left', render: (_, record) => record.index + 1 },
          ...result.columns.map(key => ({ title: key, width: key === '규격1' ? 260 : 140, render: (_: unknown, record: { row: Record<string, PreparationCell>; index: number }) => <Input aria-label={`${record.index + 1}행 ${key}`} value={record.row[key].value} status={record.row[key].kind === 'missing' || record.row[key].kind === 'conflict' ? 'warning' : undefined} onFocus={() => evidence(record.row[key])} onChange={e => edit(key, e.target.value, record.index)} /> })),
        ]} />
      </Card>
      <Card style={{ marginTop: 16 }} title="5. 검토 및 초안 저장">
        <Alert type={issues.length ? 'warning' : 'success'} title={issues.length ? '확인할 항목이 남아 있습니다' : '현재 입력값의 기본 검사 통과'} description="기본 검사는 신고 적합성이나 OCR 정확성을 보증하지 않습니다. 원문을 함께 확인하세요." />
        <Collapse style={{ marginTop: 12 }} items={[{ key: 'current', label: `현재 확인 사항 ${issues.length}개`, children: <ul>{issues.map((issue, index) => <li key={index}>{issue}</li>)}</ul> }, { key: 'initial', label: '최초 추출 진단 (수정 전 기록)', children: <ul>{result.issues.map((issue, index) => <li key={index}>{issue}</li>)}</ul> }]} />
        <Space wrap style={{ marginTop: 16 }}><Checkbox checked={reviewed} disabled={issues.length > 0} onChange={event => setReviewed(event.target.checked)}>원문 대조 완료</Checkbox><Button onClick={download}>전체 초안 JSON 저장</Button><Button onClick={copy}>품목 12열 초안 복사</Button><Tag>{reviewed ? '검토 표시됨 · 미송신' : '검토 전 초안 · 미송신'}</Tag></Space>
      </Card>
    </>}
  </main>;
}
