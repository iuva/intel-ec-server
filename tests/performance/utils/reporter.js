import { htmlReport } from "./bundle.js";
import { textSummary } from "./k6-summary.js";

export function handleSummary(data) {
    const reportName = `tests/performance/reports/report_${new Date().getTime()}.html`;
    return {
        [reportName]: htmlReport(data),
        stdout: textSummary(data, { indent: " ", enableColors: true }),
    };
}
