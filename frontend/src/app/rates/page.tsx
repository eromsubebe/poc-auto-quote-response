"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { listRates, Rate } from "@/lib/api";
import { RateTable } from "@/components/RateTable";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Plus, RefreshCw } from "lucide-react";

const MODE_OPTIONS = [
  { value: "", label: "All Modes" },
  { value: "AIR", label: "Air" },
  { value: "SEA", label: "Sea" },
  { value: "ROAD", label: "Road" },
];

const STATUS_OPTIONS = [
  { value: "", label: "All Statuses" },
  { value: "ACTIVE", label: "Active" },
  { value: "EXPIRED", label: "Expired" },
];

export default function RatesPage() {
  const [rates, setRates] = useState<Rate[]>([]);
  const [loading, setLoading] = useState(true);
  const [modeFilter, setModeFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [originFilter, setOriginFilter] = useState("");
  const [destFilter, setDestFilter] = useState("");

  async function fetchRates() {
    setLoading(true);
    try {
      const data = await listRates({
        mode: modeFilter || undefined,
        origin: originFilter || undefined,
        destination: destFilter || undefined,
        status: statusFilter || undefined,
      });
      setRates(data);
    } catch (error) {
      console.error("Failed to fetch rates:", error);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    fetchRates();
  }, [modeFilter, statusFilter, originFilter, destFilter]);

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold text-gray-900">Rate Database</h1>
        <div className="flex gap-2">
          <Button variant="outline" onClick={fetchRates} disabled={loading}>
            <RefreshCw className={`w-4 h-4 mr-2 ${loading ? "animate-spin" : ""}`} />
            Refresh
          </Button>
          <Link href="/rates/new">
            <Button>
              <Plus className="w-4 h-4 mr-2" />
              Add Rate
            </Button>
          </Link>
        </div>
      </div>

      {/* Filters */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Filters</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Mode
              </label>
              <select
                value={modeFilter}
                onChange={(e) => setModeFilter(e.target.value)}
                className="block w-40 rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 text-sm"
              >
                {MODE_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Status
              </label>
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="block w-40 rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 text-sm"
              >
                {STATUS_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Origin
              </label>
              <input
                type="text"
                value={originFilter}
                onChange={(e) => setOriginFilter(e.target.value)}
                placeholder="e.g., SIN"
                className="block w-32 rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 text-sm"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Destination
              </label>
              <input
                type="text"
                value={destFilter}
                onChange={(e) => setDestFilter(e.target.value)}
                placeholder="e.g., PHC"
                className="block w-32 rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 text-sm"
              />
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Rate Table */}
      <Card>
        <CardContent className="p-0">
          <RateTable rates={rates} loading={loading} />
        </CardContent>
      </Card>

      {/* Summary */}
      <div className="text-sm text-gray-500">
        Showing {rates.length} rate{rates.length !== 1 ? "s" : ""}
      </div>
    </div>
  );
}
