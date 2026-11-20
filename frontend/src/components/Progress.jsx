import { Line } from "react-chartjs-2";
import { Chart as C, LineElement, PointElement, LinearScale, CategoryScale, Tooltip, Legend } from "chart.js";

C.register(LineElement, PointElement, LinearScale, CategoryScale, Tooltip, Legend);

export default function Progress({ history }) {
  const cal = history.length > 0 && history.every((h) => h.calibrated);
  const data = {
    labels: history.map((h) => h.captured_on),
    datasets: [{
      label: cal ? "Wound area (cm²)" : "Wound area (px², uncalibrated)",
      data: history.map((h) => (cal ? h.area_cm2 : h.area_px)),
      borderColor: "#17736a", backgroundColor: "#17736a", tension: 0.2,
    }],
  };
  return (
    <div className="panel">
      <h3>Measured area over time</h3>
      <Line data={data} />
    </div>
  );
}
