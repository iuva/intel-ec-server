import { htmlReport } from "https://raw.githubusercontent.com/benc-uk/k6-reporter/main/dist/bundle.js";
import { textSummary } from "https://jslib.k6.io/k6-summary/0.0.1/index.js";

export function handleSummary(data) {
    const reportName = `reports/report_${new Date().getTime()}.html`;
    return {
        [reportName]: htmlReport(data),
        stdout: textSummary(data, { indent: " ", enableColors: true }),
    };
}
