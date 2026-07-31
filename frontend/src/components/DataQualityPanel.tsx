import {
  dataQualityStatusLabel,
  formatAdjustment,
  formatAdjustmentBasis,
  formatDatasetId,
} from "../dataQuality";
import { formatQuoteTime } from "../format";
import type { DataQualityReport } from "../types/dashboard";


export function DataQualityPanel({ report }: { report: DataQualityReport }) {
  const statusTone = report.status.toLowerCase();

  return (
    <section
      className={`data-quality-panel data-quality-panel--${statusTone}`}
      aria-label="数据可信度"
    >
      <div className="data-quality-panel__header">
        <div>
          <p className="data-quality-panel__eyebrow">不可变本地快照 · 后端审计</p>
          <h2>数据可信度</h2>
        </div>
        <span className={`data-quality-status data-quality-status--${statusTone}`}>
          {dataQualityStatusLabel(report.status)}
        </span>
      </div>

      <dl className="data-quality-facts">
        <div>
          <dt>合同版本</dt>
          <dd>{report.schema_version}</dd>
        </div>
        <div>
          <dt>数据来源</dt>
          <dd>{report.provider}</dd>
        </div>
        <div>
          <dt>数据范围</dt>
          <dd>{report.data_from} 至 {report.data_to}</dd>
        </div>
        <div>
          <dt>获取时间</dt>
          <dd>{formatQuoteTime(report.fetched_at)}</dd>
        </div>
        <div>
          <dt>复权口径</dt>
          <dd>{formatAdjustment(report.adjustment)}</dd>
        </div>
        <div>
          <dt>口径依据</dt>
          <dd>{formatAdjustmentBasis(report.adjustment_basis)}</dd>
        </div>
        <div>
          <dt>结构检查</dt>
          <dd>{report.integrity === "MATCH" ? "SHA-256 匹配" : report.integrity}</dd>
        </div>
        <div>
          <dt>日 K 根数</dt>
          <dd>{report.bar_count}</dd>
        </div>
        <div>
          <dt>数据集 ID</dt>
          <dd title={report.dataset_id}>{formatDatasetId(report.dataset_id)}</dd>
        </div>
        {report.audit_reference && (
          <div>
            <dt>外部审计引用</dt>
            <dd>{report.audit_reference}</dd>
          </div>
        )}
      </dl>

      {report.issues.length > 0 && (
        <div className="data-quality-panel__issues">
          {report.issues.map((issue) => (
            <p key={issue.code}>
              <strong>{issue.code}</strong> · {issue.message}
            </p>
          ))}
        </div>
      )}

      <p className="data-quality-panel__boundary">
        {report.license_note} · 文件完整性与结构检查不等于复权经济含义或策略有效性验证
      </p>
    </section>
  );
}
