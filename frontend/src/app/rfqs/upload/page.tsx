"use client";

import Link from "next/link";
import { UploadForm } from "@/components/UploadForm";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { ArrowLeft } from "lucide-react";

export default function UploadPage() {
  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <Link
        href="/rfqs"
        className="inline-flex items-center text-sm text-gray-600 hover:text-gray-900"
      >
        <ArrowLeft className="w-4 h-4 mr-1" />
        Back to RFQ Queue
      </Link>

      <Card>
        <CardHeader>
          <CardTitle>Upload RFQ Email</CardTitle>
          <CardDescription>
            Upload an .eml file to create a new RFQ. The system will automatically
            extract customer details, shipping information, and cargo data.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <UploadForm />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">What happens after upload?</CardTitle>
        </CardHeader>
        <CardContent className="text-sm text-gray-600 space-y-2">
          <p>1. Email is parsed to extract sender, subject, and body content</p>
          <p>2. Attachments (CIPL, MSDS) are processed for cargo details</p>
          <p>3. AI-powered extraction identifies key shipping information</p>
          <p>4. Automatic rate lookup finds matching carrier rates</p>
          <p>5. Draft quote is prepared for your review</p>
        </CardContent>
      </Card>
    </div>
  );
}
