"use client";

import Link from "next/link";
import { RFQListItem } from "@/lib/api";
import {
  cn,
  formatDateTime,
  getStatusColor,
  getUrgencyColor,
} from "@/lib/utils";
import { SLABadge } from "./SLABadge";
import { AlertTriangle, Package, Plane, Ship, Truck } from "lucide-react";

interface RFQTableProps {
  rfqs: RFQListItem[];
  loading?: boolean;
}

function getModeIcon(mode: string | null) {
  switch (mode) {
    case "AIR":
      return <Plane className="w-4 h-4" />;
    case "SEA":
      return <Ship className="w-4 h-4" />;
    case "ROAD":
      return <Truck className="w-4 h-4" />;
    default:
      return <Package className="w-4 h-4" />;
  }
}

export function RFQTable({ rfqs, loading }: RFQTableProps) {
  if (loading) {
    return (
      <div className="animate-pulse">
        <div className="h-10 bg-gray-200 rounded mb-2" />
        {[1, 2, 3].map((i) => (
          <div key={i} className="h-16 bg-gray-100 rounded mb-2" />
        ))}
      </div>
    );
  }

  if (rfqs.length === 0) {
    return (
      <div className="text-center py-8 text-gray-500">
        No RFQs found
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="min-w-full divide-y divide-gray-200">
        <thead className="bg-gray-50">
          <tr>
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Reference
            </th>
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Customer
            </th>
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Route
            </th>
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Status
            </th>
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              SLA
            </th>
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Assigned
            </th>
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Received
            </th>
          </tr>
        </thead>
        <tbody className="bg-white divide-y divide-gray-200">
          {rfqs.map((rfq) => (
            <tr
              key={rfq.id}
              className="hover:bg-gray-50 cursor-pointer"
            >
              <td className="px-4 py-4 whitespace-nowrap">
                <Link href={`/rfqs/${rfq.id}`} className="block">
                  <div className="flex items-center gap-2">
                    {getModeIcon(rfq.shipping_mode)}
                    <div>
                      <div className="font-medium text-gray-900">
                        {rfq.rfq_reference || rfq.id.slice(0, 8)}
                      </div>
                      {rfq.odoo_quotation_number && (
                        <div className="text-xs text-gray-500">
                          {rfq.odoo_quotation_number}
                        </div>
                      )}
                    </div>
                    {rfq.is_dangerous_goods && (
                      <AlertTriangle className="w-4 h-4 text-orange-500" title="Dangerous Goods" />
                    )}
                  </div>
                </Link>
              </td>
              <td className="px-4 py-4">
                <Link href={`/rfqs/${rfq.id}`} className="block">
                  <div className="text-sm text-gray-900">
                    {rfq.customer_name || "-"}
                  </div>
                  <div className="text-xs text-gray-500 truncate max-w-[200px]">
                    {rfq.subject}
                  </div>
                </Link>
              </td>
              <td className="px-4 py-4 whitespace-nowrap">
                <Link href={`/rfqs/${rfq.id}`} className="block">
                  <div className="text-sm">
                    {rfq.origin || "?"} → {rfq.destination || "?"}
                  </div>
                </Link>
              </td>
              <td className="px-4 py-4 whitespace-nowrap">
                <Link href={`/rfqs/${rfq.id}`} className="block">
                  <div className="flex items-center gap-2">
                    <span
                      className={cn(
                        "px-2 py-1 text-xs font-medium rounded-full",
                        getStatusColor(rfq.status)
                      )}
                    >
                      {rfq.status.replace("_", " ")}
                    </span>
                    <span
                      className={cn(
                        "px-2 py-1 text-xs font-medium rounded-full",
                        getUrgencyColor(rfq.urgency)
                      )}
                    >
                      {rfq.urgency}
                    </span>
                  </div>
                </Link>
              </td>
              <td className="px-4 py-4 whitespace-nowrap">
                <SLABadge
                  deadline={rfq.sla_deadline_at}
                  breached={rfq.sla_breached}
                />
              </td>
              <td className="px-4 py-4 whitespace-nowrap text-sm text-gray-500">
                {rfq.assigned_agent || "-"}
              </td>
              <td className="px-4 py-4 whitespace-nowrap text-sm text-gray-500">
                {formatDateTime(rfq.received_at || rfq.created_at)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
