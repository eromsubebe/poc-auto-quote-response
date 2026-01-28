"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { listRFQs, RFQListItem } from "@/lib/api";
import { RFQTable } from "@/components/RFQTable";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Upload, RefreshCw } from "lucide-react";

const STATUS_OPTIONS = [
  { value: "", label: "All Statuses" },
  { value: "received", label: "Received" },
  { value: "parsing", label: "Parsing" },
  { value: "rates_lookup", label: "Rates Lookup" },
  { value: "rates_pending", label: "Rates Pending" },
  { value: "rates_found", label: "Rates Found" },
  { value: "quote_draft", label: "Quote Draft" },
  { value: "quote_review", label: "Quote Review" },
  { value: "sent", label: "Sent" },
];

const URGENCY_OPTIONS = [
  { value: "", label: "All Urgency" },
  { value: "STANDARD", label: "Standard" },
  { value: "URGENT", label: "Urgent" },
];

export default function RFQsPage() {
  const [rfqs, setRfqs] = useState<RFQListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState("");
  const [urgencyFilter, setUrgencyFilter] = useState("");

  async function fetchRFQs() {
    setLoading(true);
    try {
      const data = await listRFQs(
        statusFilter || undefined,
        urgencyFilter || undefined
      );
      setRfqs(data);
    } catch (error) {
      console.error("Failed to fetch RFQs:", error);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    fetchRFQs();
  }, [statusFilter, urgencyFilter]);

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold text-gray-900">RFQ Queue</h1>
        <div className="flex gap-2">
          <Button variant="outline" onClick={fetchRFQs} disabled={loading}>
            <RefreshCw className={`w-4 h-4 mr-2 ${loading ? "animate-spin" : ""}`} />
            Refresh
          </Button>
          <Link href="/rfqs/upload">
            <Button>
              <Upload className="w-4 h-4 mr-2" />
              Upload RFQ
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
                Status
              </label>
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="block w-48 rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 text-sm"
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
                Urgency
              </label>
              <select
                value={urgencyFilter}
                onChange={(e) => setUrgencyFilter(e.target.value)}
                className="block w-48 rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 text-sm"
              >
                {URGENCY_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* RFQ Table */}
      <Card>
        <CardContent className="p-0">
          <RFQTable rfqs={rfqs} loading={loading} />
        </CardContent>
      </Card>

      {/* Summary */}
      <div className="text-sm text-gray-500">
        Showing {rfqs.length} RFQ{rfqs.length !== 1 ? "s" : ""}
      </div>
    </div>
  );
}
