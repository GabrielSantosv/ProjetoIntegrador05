import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";

export function RiskPieChart({ risk }: { risk: number }) {
  const safeRisk = Math.min(100, Math.max(0, risk));
  const data = [
    { name: "Risco", value: safeRisk, color: "#b91c1c" },
    { name: "Margem", value: 100 - safeRisk, color: "#0f766e" },
  ];

  return (
    <div className="h-52 w-full">
      <ResponsiveContainer>
        <PieChart>
          <Pie data={data} innerRadius={58} outerRadius={82} dataKey="value" paddingAngle={2}>
            {data.map((entry) => (
              <Cell key={entry.name} fill={entry.color} />
            ))}
          </Pie>
          <Tooltip formatter={(value) => `${value}%`} />
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
}
