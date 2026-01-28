"use client";

import { Rate } from "@/lib/api";
import {
  cn,
  formatCurrency,
  formatDate,
  getDaysUntilExpiry,
  getExpiryColor,
  getStatusColor,
} from "@/lib/utils";
import { Plane, Ship, Truck } from "lucide-react";

interface RateTableProps {
  rates: Rate[];
  loading?: boolean;
}

function getModeIcon(mode: string) {
  switch (mode) {
    case "AIR":
      return <Plane className="w-4 h-4" />;
    case "SEA":
      return <Ship className="w-4 h-4" />;
    case "ROAD":
      return <Truck className="w-4 h-4" />;
    default:
      return null;
  }
}

export function RateTable({ rates, loading }: RateTableProps) {
  if (loading) {
    return (
      <div className="animate-pulse">
        <div className="h-10 bg-gray-200 rounded mb-2" />
        {[1, 2, 3].map((i) => (
          <div key={i} className="h-14 bg-gray-100 rounded mb-2" />
        ))}
      </div>
    );
  }

  if (rates.length === 0) {
    return (
      <div className="text-center py-8 text-gray-500">
        No rates found
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="min-w-full divide-y divide-gray-200">
        <thead className="bg-gray-50">
          <tr>
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Carrier
            </th>
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Route
            </th>
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Mode
            </th>
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Rate
            </th>
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Min Charge
            </th>
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              DG Surcharge
            </th>
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Expiry
            </th>
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Status
            </th>
          </tr>
        </thead>
        <tbody className="bg-white divide-y divide-gray-200">
          {rates.map((rate) => {
            const daysUntilExpiry = getDaysUntilExpiry(rate.valid_to);
            return (
              <tr key={rate.id} className="hover:bg-gray-50">
                <td className="px-4 py-4 whitespace-nowrap">
                  <div className="font-medium text-gray-900">
                    {rate.carrier_name}
                  </div>
                  <div className="text-xs text-gray-500">{rate.source}</div>
                </td>
                <td className="px-4 py-4 whitespace-nowrap">
                  <div className="text-sm">
                    {rate.origin_port} → {rate.destination_port}
                  </div>
                </td>
                <td className="px-4 py-4 whitespace-nowrap">
                  <div className="flex items-center gap-1">
                    {getModeIcon(rate.mode)}
                    <span>{rate.mode}</span>
                  </div>
                </td>
                <td className="px-4 py-4 whitespace-nowrap">
                  <div className="font-medium">
                    {formatCurrency(rate.rate_per_unit, rate.currency)}
                  </div>
                  <div className="text-xs text-gray-500">per {rate.unit}</div>
                </td>
                <td className="px-4 py-4 whitespace-nowrap text-sm">
                  {rate.minimum_charge
                    ? formatCurrency(rate.minimum_charge, rate.currency)
                    : "-"}
                </td>
                <td className="px-4 py-4 whitespace-nowrap text-sm">
                  {rate.dg_surcharge_pct ? `${rate.dg_surcharge_pct}%` : "-"}
                </td>
                <td className="px-4 py-4 whitespace-nowrap">
                  <div className={cn("text-sm", getExpiryColor(daysUntilExpiry))}>
                    {formatDate(rate.valid_to)}
                  </div>
                  <div className="text-xs text-gray-500">
                    {daysUntilExpiry < 0
                      ? "Expired"
                      : `${daysUntilExpiry} days`}
                  </div>
                </td>
                <td className="px-4 py-4 whitespace-nowrap">
                  <span
                    className={cn(
                      "px-2 py-1 text-xs font-medium rounded-full",
                      getStatusColor(rate.status)
                    )}
                  >
                    {rate.status}
                  </span>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
