"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";
import { CheckCircle2, Leaf } from "lucide-react";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { api } from "@/lib/api";

export default function PublicPcfRequestPage({ params }: { params: { orgId: string } }) {
  const [requesterName, setRequesterName] = useState("");
  const [requesterEmail, setRequesterEmail] = useState("");
  const [requesterCompany, setRequesterCompany] = useState("");
  const [productName, setProductName] = useState("");
  const [message, setMessage] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [submitted, setSubmitted] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await api.submitPcfRequest({
        org_id: params.orgId,
        requester_name: requesterName.trim(),
        requester_email: requesterEmail.trim(),
        requester_company: requesterCompany.trim(),
        product_name: productName.trim(),
        message: message.trim(),
      });
      setSubmitted(true);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="min-h-screen bg-background">
      <header className="border-b">
        <div className="mx-auto flex max-w-2xl items-center justify-between gap-3 px-4 py-3">
          <div className="flex items-center gap-2.5">
            <span className="flex h-7 w-7 items-center justify-center rounded-md bg-primary text-primary-foreground">
              <Leaf className="h-4 w-4" aria-hidden />
            </span>
            <span className="text-body font-display font-semibold">Carbon Analyzer</span>
            <Badge variant="neutral">Public request</Badge>
          </div>
          <Button variant="ghost" size="sm" asChild>
            <Link href="/">Home</Link>
          </Button>
        </div>
      </header>

      <main className="mx-auto max-w-2xl px-4 py-8">
        {submitted ? (
          <Alert variant="success">
            <CheckCircle2 className="h-4 w-4" />
            <AlertTitle>Request submitted</AlertTitle>
            <AlertDescription>
              Your product carbon footprint request has been sent. The organization will review
              it and respond with a share link if they can fulfil it.
            </AlertDescription>
          </Alert>
        ) : (
          <Card>
            <CardHeader>
              <CardTitle>Request a product carbon footprint</CardTitle>
              <CardDescription>
                Submit a request for a published product footprint from this organization. No
                account is required.
              </CardDescription>
            </CardHeader>
            <CardContent>
              {error ? (
                <Alert className="mb-4" variant="destructive">
                  <AlertDescription>{error}</AlertDescription>
                </Alert>
              ) : null}
              <form className="space-y-4" onSubmit={handleSubmit}>
                <div className="space-y-2">
                  <Label htmlFor="requester-company">Your company</Label>
                  <Input
                    id="requester-company"
                    placeholder="Acme Retail Co."
                    required
                    value={requesterCompany}
                    onChange={(event) => setRequesterCompany(event.target.value)}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="product-name">Product name</Label>
                  <Input
                    id="product-name"
                    placeholder="Insulated water bottle"
                    required
                    value={productName}
                    onChange={(event) => setProductName(event.target.value)}
                  />
                </div>
                <div className="grid gap-4 sm:grid-cols-2">
                  <div className="space-y-2">
                    <Label htmlFor="requester-name">Your name</Label>
                    <Input
                      id="requester-name"
                      placeholder="Alex Analyst"
                      required
                      value={requesterName}
                      onChange={(event) => setRequesterName(event.target.value)}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="requester-email">Your email</Label>
                    <Input
                      id="requester-email"
                      type="email"
                      placeholder="alex@acmeretail.com"
                      required
                      value={requesterEmail}
                      onChange={(event) => setRequesterEmail(event.target.value)}
                    />
                  </div>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="message">Message</Label>
                  <Textarea
                    id="message"
                    placeholder="Tell us why you need this footprint and any reporting context."
                    required
                    rows={4}
                    value={message}
                    onChange={(event) => setMessage(event.target.value)}
                  />
                </div>
                <Button disabled={submitting} type="submit">
                  {submitting ? "Submitting..." : "Submit request"}
                </Button>
              </form>
            </CardContent>
          </Card>
        )}
      </main>
    </div>
  );
}
