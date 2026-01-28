"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import {
  getRFQ,
  listRates,
  assignRateToRFQ,
  approveRFQ,
  exportRFQ,
  RFQDetail,
  Rate,
} from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { SLABadge } from "@/components/SLABadge";
import {
  cn,
  formatCurrency,
  formatDateTime,
  getStatusColor,
  getUrgencyColor,
} from "@/lib/utils";
import {
  AlertTriangle,
  ArrowLeft,
  CheckCircle,
  Download,
  FileText,
  Loader2,
  Plane,
  Ship,
  Truck,
} from "lucide-react";

function getModeIcon(mode: string | null) {
  switch (mode) {
    case "AIR":
      return <Plane className="w-5 h-5" />;
    case "SEA":
      return <Ship className="w-5 h-5" />;
    case "ROAD":
      return <Truck className="w-5 h-5" />;
    default:
      return <FileText className="w-5 h-5" />;
  }
}

export default function RFQDetailPage() {
  const params = useParams();
  const router = useRouter();
  const rfqId = params.id as string;

  const [rfq, setRfq] = useState<RFQDetail | null>(null);
  const [rates, setRates] = useState<Rate[]>([]);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<"details" | "parsed" | "audit">("details");

  useEffect(() => {
    async function fetchData() {
      try {
        const [rfqData, ratesData] = await Promise.all([
          getRFQ(rfqId),
          listRates({ status: "ACTIVE" }),
        ]);
        setRfq(rfqData);
        setRates(ratesData);
      } catch (error) {
        console.error("Failed to fetch RFQ:", error);
      } finally {
        setLoading(false);
      }
    }
    fetchData();
  }, [rfqId]);

  const handleAssignRate = async (rateId: string) => {
    setActionLoading("assign");
    try {
      const updated = await assignRateToRFQ(rfqId, rateId);
      setRfq(updated);
    } catch (error) {
      console.error("Failed to assign rate:", error);
    } finally {
      setActionLoading(null);
    }
  };

  const handleApprove = async () => {
    setActionLoading("approve");
    try {
      const updated = await approveRFQ(rfqId);
      setRfq(updated);
    } catch (error) {
      console.error("Failed to approve:", error);
    } finally {
      setActionLoading(null);
    }
  };

  const handleExport = async (format: "json" | "csv" | "pdf") => {
    setActionLoading(`export-${format}`);
    try {
      const result = await exportRFQ(rfqId, format);
      if (format === "json") {
        const blob = new Blob([JSON.stringify(result, null, 2)], {
          type: "application/json",
        });
        downloadBlob(blob, `draft_pack_${rfq?.rfq_reference || rfqId}.json`);
      } else {
        downloadBlob(result as Blob, `draft_pack_${rfq?.rfq_reference || rfqId}.${format}`);
      }
    } catch (error) {
      console.error("Export failed:", error);
    } finally {
      setActionLoading(null);
    }
  };

  const downloadBlob = (blob: Blob, filename: string) => {
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-blue-500" />
      </div>
    );
  }

  if (!rfq) {
    return (
      <div className="text-center py-12">
        <h2 className="text-xl font-semibold text-gray-900">RFQ not found</h2>
        <Link href="/rfqs" className="text-blue-600 hover:underline mt-2 block">
          Back to RFQ Queue
        </Link>
      </div>
    );
  }

  const emailData = rfq.parsed_email_json ? JSON.parse(rfq.parsed_email_json) : null;
  const ciplData = rfq.parsed_cipl_json ? JSON.parse(rfq.parsed_cipl_json) : null;
  const msdsData = rfq.parsed_msds_json ? JSON.parse(rfq.parsed_msds_json) : null;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <Link
            href="/rfqs"
            className="inline-flex items-center text-sm text-gray-600 hover:text-gray-900 mb-2"
          >
            <ArrowLeft className="w-4 h-4 mr-1" />
            Back to Queue
          </Link>
          <div className="flex items-center gap-3">
            {getModeIcon(rfq.shipping_mode)}
            <h1 className="text-2xl font-bold text-gray-900">
              {rfq.rfq_reference || rfq.id.slice(0, 8)}
            </h1>
            {rfq.is_dangerous_goods && (
              <Badge className="bg-orange-100 text-orange-800">
                <AlertTriangle className="w-3 h-3 mr-1" />
                DG
              </Badge>
            )}
          </div>
          <p className="text-gray-600 mt-1">{rfq.subject}</p>
        </div>
        <div className="flex items-center gap-2">
          <span className={cn("px-3 py-1 rounded-full text-sm font-medium", getStatusColor(rfq.status))}>
            {rfq.status.replace("_", " ")}
          </span>
          <span className={cn("px-3 py-1 rounded-full text-sm font-medium", getUrgencyColor(rfq.urgency))}>
            {rfq.urgency}
          </span>
          <SLABadge deadline={rfq.sla_deadline_at} breached={rfq.sla_breached} />
        </div>
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200">
        <nav className="-mb-px flex space-x-8">
          {[
            { id: "details", label: "Details" },
            { id: "parsed", label: "Parsed Data" },
            { id: "audit", label: "Audit Log" },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as typeof activeTab)}
              className={cn(
                "whitespace-nowrap pb-4 px-1 border-b-2 font-medium text-sm",
                activeTab === tab.id
                  ? "border-blue-500 text-blue-600"
                  : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300"
              )}
            >
              {tab.label}
            </button>
          ))}
        </nav>
      </div>

      {/* Tab Content */}
      {activeTab === "details" && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Main Info */}
          <div className="lg:col-span-2 space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>Shipment Details</CardTitle>
              </CardHeader>
              <CardContent className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-sm font-medium text-gray-500">Customer</label>
                  <p className="font-medium">{rfq.customer_name || "-"}</p>
                  <p className="text-sm text-gray-600">{rfq.customer_email}</p>
                </div>
                <div>
                  <label className="text-sm font-medium text-gray-500">Route</label>
                  <p className="font-medium">{rfq.origin || "?"} → {rfq.destination || "?"}</p>
                  <p className="text-sm text-gray-600">{rfq.shipping_mode || "Mode TBD"}</p>
                </div>
                <div>
                  <label className="text-sm font-medium text-gray-500">Received</label>
                  <p>{formatDateTime(rfq.received_at)}</p>
                </div>
                <div>
                  <label className="text-sm font-medium text-gray-500">SLA Deadline</label>
                  <p>{formatDateTime(rfq.sla_deadline_at)}</p>
                  <p className="text-sm text-gray-600">{rfq.sla_target_hours}h target</p>
                </div>
              </CardContent>
            </Card>

            {/* Rate Assignment */}
            <Card>
              <CardHeader>
                <CardTitle>Rate Assignment</CardTitle>
              </CardHeader>
              <CardContent>
                {rfq.rate_id ? (
                  <div className="bg-green-50 p-4 rounded-lg">
                    <div className="flex items-center gap-2 mb-2">
                      <CheckCircle className="w-5 h-5 text-green-600" />
                      <span className="font-medium text-green-800">Rate Assigned</span>
                    </div>
                    <div className="grid grid-cols-2 gap-4 text-sm">
                      <div>
                        <label className="text-gray-500">Rate Amount</label>
                        <p className="font-medium">
                          {formatCurrency(rfq.rate_amount, rfq.rate_currency || "USD")}
                        </p>
                      </div>
                      <div>
                        <label className="text-gray-500">Estimated Cost</label>
                        <p className="font-medium">
                          {formatCurrency(rfq.estimated_cost, rfq.rate_currency || "USD")}
                        </p>
                      </div>
                    </div>
                  </div>
                ) : (
                  <div>
                    <p className="text-gray-600 mb-4">
                      Select a rate to assign to this RFQ:
                    </p>
                    <div className="space-y-2 max-h-64 overflow-y-auto">
                      {rates
                        .filter(
                          (r) =>
                            (!rfq.shipping_mode || r.mode === rfq.shipping_mode) &&
                            (!rfq.destination || r.destination_port.includes(rfq.destination.slice(0, 3)))
                        )
                        .slice(0, 10)
                        .map((rate) => (
                          <div
                            key={rate.id}
                            className="flex items-center justify-between p-3 bg-gray-50 rounded-lg hover:bg-gray-100"
                          >
                            <div>
                              <div className="font-medium">{rate.carrier_name}</div>
                              <div className="text-sm text-gray-600">
                                {rate.origin_port} → {rate.destination_port} ({rate.mode})
                              </div>
                            </div>
                            <div className="flex items-center gap-3">
                              <div className="text-right">
                                <div className="font-medium">
                                  {formatCurrency(rate.rate_per_unit, rate.currency)}
                                </div>
                                <div className="text-xs text-gray-500">per {rate.unit}</div>
                              </div>
                              <Button
                                size="sm"
                                onClick={() => handleAssignRate(rate.id)}
                                disabled={actionLoading === "assign"}
                              >
                                {actionLoading === "assign" ? (
                                  <Loader2 className="w-4 h-4 animate-spin" />
                                ) : (
                                  "Assign"
                                )}
                              </Button>
                            </div>
                          </div>
                        ))}
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          </div>

          {/* Sidebar Actions */}
          <div className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>Actions</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                {rfq.status === "quote_review" && (
                  <Button
                    className="w-full"
                    onClick={handleApprove}
                    disabled={actionLoading === "approve"}
                  >
                    {actionLoading === "approve" ? (
                      <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    ) : (
                      <CheckCircle className="w-4 h-4 mr-2" />
                    )}
                    Approve & Send
                  </Button>
                )}
                <Button
                  variant="outline"
                  className="w-full"
                  onClick={() => handleExport("pdf")}
                  disabled={!!actionLoading}
                >
                  {actionLoading === "export-pdf" ? (
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  ) : (
                    <Download className="w-4 h-4 mr-2" />
                  )}
                  Export PDF
                </Button>
                <Button
                  variant="outline"
                  className="w-full"
                  onClick={() => handleExport("csv")}
                  disabled={!!actionLoading}
                >
                  {actionLoading === "export-csv" ? (
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  ) : (
                    <Download className="w-4 h-4 mr-2" />
                  )}
                  Export CSV
                </Button>
                <Button
                  variant="outline"
                  className="w-full"
                  onClick={() => handleExport("json")}
                  disabled={!!actionLoading}
                >
                  {actionLoading === "export-json" ? (
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  ) : (
                    <Download className="w-4 h-4 mr-2" />
                  )}
                  Export JSON
                </Button>
              </CardContent>
            </Card>

            {rfq.odoo_quotation_number && (
              <Card>
                <CardHeader>
                  <CardTitle>Odoo Quote</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-2xl font-bold text-blue-600">
                    {rfq.odoo_quotation_number}
                  </p>
                  <p className="text-sm text-gray-600">
                    Order ID: {rfq.odoo_sale_order_id}
                  </p>
                </CardContent>
              </Card>
            )}

            <Card>
              <CardHeader>
                <CardTitle>Timeline</CardTitle>
              </CardHeader>
              <CardContent className="text-sm space-y-2">
                <div className="flex justify-between">
                  <span className="text-gray-500">Received</span>
                  <span>{formatDateTime(rfq.received_at)}</span>
                </div>
                {rfq.parsing_completed_at && (
                  <div className="flex justify-between">
                    <span className="text-gray-500">Parsed</span>
                    <span>{formatDateTime(rfq.parsing_completed_at)}</span>
                  </div>
                )}
                {rfq.rate_found_at && (
                  <div className="flex justify-between">
                    <span className="text-gray-500">Rate Found</span>
                    <span>{formatDateTime(rfq.rate_found_at)}</span>
                  </div>
                )}
                {rfq.quote_drafted_at && (
                  <div className="flex justify-between">
                    <span className="text-gray-500">Quote Drafted</span>
                    <span>{formatDateTime(rfq.quote_drafted_at)}</span>
                  </div>
                )}
                {rfq.quote_sent_at && (
                  <div className="flex justify-between">
                    <span className="text-gray-500">Quote Sent</span>
                    <span>{formatDateTime(rfq.quote_sent_at)}</span>
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </div>
      )}

      {activeTab === "parsed" && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {emailData && (
            <Card>
              <CardHeader>
                <CardTitle>Email Data</CardTitle>
              </CardHeader>
              <CardContent>
                <pre className="text-xs bg-gray-50 p-4 rounded overflow-auto max-h-96">
                  {JSON.stringify(emailData, null, 2)}
                </pre>
              </CardContent>
            </Card>
          )}
          {ciplData && (
            <Card>
              <CardHeader>
                <CardTitle>CIPL Data</CardTitle>
              </CardHeader>
              <CardContent>
                <pre className="text-xs bg-gray-50 p-4 rounded overflow-auto max-h-96">
                  {JSON.stringify(ciplData, null, 2)}
                </pre>
              </CardContent>
            </Card>
          )}
          {msdsData && (
            <Card>
              <CardHeader>
                <CardTitle>MSDS Data</CardTitle>
              </CardHeader>
              <CardContent>
                <pre className="text-xs bg-gray-50 p-4 rounded overflow-auto max-h-96">
                  {JSON.stringify(msdsData, null, 2)}
                </pre>
              </CardContent>
            </Card>
          )}
        </div>
      )}

      {activeTab === "audit" && (
        <Card>
          <CardHeader>
            <CardTitle>Audit Log</CardTitle>
          </CardHeader>
          <CardContent>
            {rfq.audit_log.length > 0 ? (
              <div className="space-y-3">
                {rfq.audit_log.map((entry, idx) => (
                  <div
                    key={idx}
                    className="flex items-start gap-4 p-3 bg-gray-50 rounded-lg"
                  >
                    <div className="flex-1">
                      <div className="font-medium">{entry.event}</div>
                      {entry.old_value && (
                        <div className="text-sm text-gray-600">
                          From: {entry.old_value}
                        </div>
                      )}
                      {entry.new_value && (
                        <div className="text-sm text-gray-600">
                          To: {entry.new_value}
                        </div>
                      )}
                    </div>
                    <div className="text-sm text-gray-500">
                      {formatDateTime(entry.timestamp)}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-gray-500">No audit log entries</p>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
