import React from "react";
import Sidebar from "../components/common/Sidebar";
import TopBar from "../components/common/TopBar";
import { Line, Doughnut, Bar } from "react-chartjs-2";
import {
  Chart as ChartJS,
  LineElement,
  BarElement,
  ArcElement,
  CategoryScale,
  LinearScale,
  PointElement,
  Tooltip,
  Legend
} from "chart.js";

ChartJS.register(
  LineElement,
  BarElement,
  ArcElement,
  CategoryScale,
  LinearScale,
  PointElement,
  Tooltip,
  Legend
);

export default function Dashboard() {
  return (
    <div className="min-h-screen bg-[#050d1b] text-white flex">
      <Sidebar />
      <main className="flex-1 md:ml-64 p-4 md:p-6">
        <TopBar />

        {/* Dashboard content goes here */}
        {/* Stats + Charts */}
      </main>
    </div>
  );
}
