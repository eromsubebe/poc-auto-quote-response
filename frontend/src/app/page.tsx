"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  getDashboardOverview,
  getSLAAlerts,
  listRates,
  DashboardOverview,
  SLAAlerts,
  Rate,
} from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
  AlertTriangle,
  CheckCircle,
  Clock,
  FileText,
  Package,
  XCircle,
} from "lucide-react";
import { cn, formatDate, getDaysUntilExpiry, getExpiryColor } from "@/lib/utils";

export default function DashboardPage() {
  const [overview, setOverview] = useState<DashboardOverview | null>(null);
  const [slaAlerts, setSlaAlerts] = useState<SLAAlerts | null>(null);
  const [expiringRates, setExpiringRates] = useState<Rate[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchData() {
      try {
        const [overviewData, alertsData, ratesData] = await Promise.all([
          getDashboardOverview(),
          getSLAAlerts(),
          listRates({ status: "ACTIVE" }),
        ]);
        setOverview(overviewData);
        setSlaAlerts(alertsData);
        // Filter to rates expiring within 7 days
        const expiring = ratesData.filter(
          (r) => getDaysUntilExpiry(r.valid_to) <= 7 && getDaysUntilExpiry(r.valid_to) >= 0
        );
        setExpiringRates(expiring);
      } catch (error) {
        console.error("Failed to fetch dashboard data:", error);
      } finally {
        setLoading(false);
      }
    }
    fetchData();
  }, []);

  if (loading) {
    return (
      <div className="animate-pulse space-y-4">
        <div className="h-8 w-48 bg-gray-200 rounded" />
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="h-32 bg-gray-100 rounded-lg" />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
        <Link href="/rfqs/upload">
          <Button>
            <FileText className="w-4 h-4 mr-2" />
            Upload RFQ
          </Button>
        </Link>
      </div>

      {/* Status Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total RFQs</CardTitle>
            <Package className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{overview?.total || 0}</div>
            <p className="text-xs text-muted-foreground">
              {overview?.urgent_count || 0} urgent
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Pending Action</CardTitle>
            <Clock className="h-4 w-4 text-yellow-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {(overview?.by_status?.rates_pending || 0) +
                (overview?.by_status?.quote_review || 0)}
            </div>
            <p className="text-xs text-muted-foreground">
              Awaiting rates or review
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">SLA Breached</CardTitle>
            <XCircle className="h-4 w-4 text-red-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-red-600">
              {slaAlerts?.summary.breached_count || 0}
            </div>
            <p className="text-xs text-muted-foreground">
              {slaAlerts?.summary.approaching_count || 0} approaching deadline
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Completed</CardTitle>
            <CheckCircle className="h-4 w-4 text-green-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">
              {overview?.by_status?.sent || 0}
            </div>
            <p className="text-xs text-muted-foreground">Quotes sent</p>
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* SLA Alerts */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <AlertTriangle className="w-5 h-5 text-orange-500" />
              SLA Alerts
            </CardTitle>
          </CardHeader>
          <CardContent>
            {slaAlerts &&
            (slaAlerts.summary.breached_count > 0 ||
              slaAlerts.summary.approaching_count > 0) ? (
              <div className="space-y-3">
                {slaAlerts.breached?.slice(0, 3).map((alert) => (
                  <Link
                    key={alert.rfq_id}
                    href={`/rfqs/${alert.rfq_id}`}
                    className="block p-3 bg-red-50 rounded-lg hover:bg-red-100"
                  >
                    <div className="flex justify-between items-start">
                      <div>
                        <div className="font-medium text-red-800">
                          {alert.rfq_reference || alert.rfq_id.slice(0, 8)}
                        </div>
                        <div className="text-sm text-red-600">
                          {alert.customer_name}
                        </div>
                      </div>
                      <span className="text-xs bg-red-200 text-red-800 px-2 py-1 rounded">
                        BREACHED
                      </span>
                    </div>
                  </Link>
                ))}
                {slaAlerts.approaching.slice(0, 3).map((alert) => (
                  <Link
                    key={alert.rfq_id}
                    href={`/rfqs/${alert.rfq_id}`}
                    className="block p-3 bg-orange-50 rounded-lg hover:bg-orange-100"
                  >
                    <div className="flex justify-between items-start">
                      <div>
                        <div className="font-medium text-orange-800">
                          {alert.rfq_reference || alert.rfq_id.slice(0, 8)}
                        </div>
                        <div className="text-sm text-orange-600">
                          {alert.customer_name}
                        </div>
                      </div>
                      <span className="text-xs bg-orange-200 text-orange-800 px-2 py-1 rounded">
                        {alert.hours_remaining.toFixed(1)}h left
                      </span>
                    </div>
                  </Link>
                ))}
              </div>
            ) : (
              <div className="text-center py-6 text-gray-500">
                <CheckCircle className="w-8 h-8 mx-auto mb-2 text-green-500" />
                No SLA alerts
              </div>
            )}
          </CardContent>
        </Card>

        {/* Expiring Rates */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Clock className="w-5 h-5 text-yellow-500" />
              Expiring Rates
            </CardTitle>
          </CardHeader>
          <CardContent>
            {expiringRates.length > 0 ? (
              <div className="space-y-3">
                {expiringRates.slice(0, 5).map((rate) => {
                  const daysUntil = getDaysUntilExpiry(rate.valid_to);
                  return (
                    <div
                      key={rate.id}
                      className="p-3 bg-gray-50 rounded-lg flex justify-between items-center"
                    >
                      <div>
                        <div className="font-medium">{rate.carrier_name}</div>
                        <div className="text-sm text-gray-600">
                          {rate.origin_port} → {rate.destination_port} ({rate.mode})
                        </div>
                      </div>
                      <div className="text-right">
                        <span
                          className={cn(
                            "text-sm font-medium",
                            getExpiryColor(daysUntil)
                          )}
                        >
                          {formatDate(rate.valid_to)}
                        </span>
                        <div className="text-xs text-gray-500">
                          {daysUntil} day{daysUntil !== 1 ? "s" : ""} left
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            ) : (
              <div className="text-center py-6 text-gray-500">
                <CheckCircle className="w-8 h-8 mx-auto mb-2 text-green-500" />
                No rates expiring soon
              </div>
            )}
            <Link href="/rates" className="block mt-4">
              <Button variant="outline" className="w-full">
                View All Rates
              </Button>
            </Link>
          </CardContent>
        </Card>
      </div>

      {/* Status Breakdown */}
      <Card>
        <CardHeader>
          <CardTitle>RFQ Status Breakdown</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-8 gap-4">
            {[
              { status: "received", label: "Received", color: "bg-blue-100" },
              { status: "parsing", label: "Parsing", color: "bg-yellow-100" },
              { status: "rates_lookup", label: "Rate Lookup", color: "bg-purple-100" },
              { status: "rates_pending", label: "Rates Pending", color: "bg-orange-100" },
              { status: "rates_found", label: "Rates Found", color: "bg-green-100" },
              { status: "quote_draft", label: "Draft", color: "bg-indigo-100" },
              { status: "quote_review", label: "Review", color: "bg-cyan-100" },
              { status: "sent", label: "Sent", color: "bg-emerald-100" },
            ].map(({ status, label, color }) => (
              <div key={status} className={cn("p-3 rounded-lg text-center", color)}>
                <div className="text-2xl font-bold">
                  {overview?.by_status?.[status] || 0}
                </div>
                <div className="text-xs font-medium">{label}</div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
