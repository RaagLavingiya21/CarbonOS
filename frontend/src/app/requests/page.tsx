"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { ArrowLeft, Copy, Inbox } from "lucide-react";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { ErrorState } from "@/components/ui/error-state";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { AnalysisSummary, PcfRequest, api } from "@/lib/api";

function statusBadgeVariant(status: string) {
  if (status === "open") return "secondary" as const;
  if (status === "fulfilled") return "default" as const;
  return "outline" as const;
}

export default function RequestsPage() {
  const [requests, setRequests] = useState<PcfRequest[]>([]);
  const [publishedProducts, setPublishedProducts] = useState<AnalysisSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedProductByRequest, setSelectedProductByRequest] = useState<
    Record<number, string>
  >({});
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [fulfilLinks, setFulfilLinks] = useState<Record<number, string>>({});

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [requestRows, products] = await Promise.all([
        api.listPcfRequests(),
        api.listAnalyses({ status: "published" }),
      ]);
      setRequests(requestRows);
      setPublishedProducts(products);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadData();
  }, [loadData]);

  async function handleFulfil(requestId: number) {
    const productId = Number(selectedProductByRequest[requestId]);
    if (!Number.isFinite(productId) || productId <= 0) return;
    setActionLoading(`fulfil-${requestId}`);
    setError(null);
    try {
      const result = await api.fulfilPcfRequest(requestId, productId);
      const link = `${window.location.origin}/shared/${result.share_token}`;
      setFulfilLinks((current) => ({ ...current, [requestId]: link }));
      await loadData();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setActionLoading(null);
    }
  }

  async function handleDecline(requestId: number) {
    setActionLoading(`decline-${requestId}`);
    setError(null);
    try {
      await api.declinePcfRequest(requestId);
      await loadData();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setActionLoading(null);
    }
  }

  async function copyLink(link: string) {
    await navigator.clipboard.writeText(link);
  }

  const openRequests = requests.filter((request) => request.status === "open");

  return (
    <div className="space-y-6">
      <Button asChild variant="ghost" className="-ml-3">
        <Link href="/">
          <ArrowLeft className="h-4 w-4" />
          Back to dashboard
        </Link>
      </Button>

      <section>
        <div className="flex items-center gap-2">
          <Inbox className="h-6 w-6 text-muted-foreground" />
          <h1 className="text-h1">PCF requests</h1>
        </div>
        <p className="mt-2 text-small text-muted-foreground">
          Inbound product carbon footprint requests for your active organization.
        </p>
      </section>

      {error ? (
        <Alert variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      ) : null}

      {loading ? (
        <div className="space-y-4">
          {[1, 2, 3].map((item) => (
            <Skeleton key={item} className="h-32 rounded-lg" />
          ))}
        </div>
      ) : error && requests.length === 0 ? (
        <ErrorState title="Couldn't load requests" message={error} onRetry={() => void loadData()} />
      ) : (
        <div className="space-y-4">
          {requests.length === 0 ? (
            <Card>
              <CardContent className="py-10 text-center text-small text-muted-foreground">
                No PCF requests yet. Share your public request link from Settings.
              </CardContent>
            </Card>
          ) : (
            requests.map((request) => {
              const shareLink =
                fulfilLinks[request.request_id] ??
                (request.share_token
                  ? `${window.location.origin}/shared/${request.share_token}`
                  : null);

              return (
                <Card key={request.request_id}>
                  <CardHeader>
                    <div className="flex flex-wrap items-center gap-2">
                      <CardTitle>{request.product_name ?? "Unnamed product"}</CardTitle>
                      <Badge variant={statusBadgeVariant(request.status)}>{request.status}</Badge>
                    </div>
                    <CardDescription>
                      {request.requester_company ?? "Unknown company"} ·{" "}
                      {request.requester_name ?? "Unknown requester"}
                      {request.requester_email ? ` · ${request.requester_email}` : ""}
                      {request.created_at
                        ? ` · ${new Date(request.created_at).toLocaleString()}`
                        : ""}
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    {request.message ? (
                      <p className="text-small text-muted-foreground">{request.message}</p>
                    ) : null}

                    {request.status === "open" ? (
                      <div className="space-y-3">
                        <div className="space-y-2">
                          <Label htmlFor={`product-${request.request_id}`}>
                            Fulfil with published footprint
                          </Label>
                          <Select
                            value={selectedProductByRequest[request.request_id] ?? ""}
                            onValueChange={(value) =>
                              setSelectedProductByRequest((current) => ({
                                ...current,
                                [request.request_id]: value,
                              }))
                            }
                          >
                            <SelectTrigger id={`product-${request.request_id}`}>
                              <SelectValue placeholder="Select a published footprint" />
                            </SelectTrigger>
                            <SelectContent>
                              {publishedProducts.map((product) => (
                                <SelectItem
                                  key={product.product_id}
                                  value={String(product.product_id)}
                                >
                                  {product.product_name} (v{product.version ?? 1})
                                </SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                        </div>
                        <div className="flex flex-wrap gap-2">
                          <Button
                            disabled={
                              actionLoading === `fulfil-${request.request_id}` ||
                              !selectedProductByRequest[request.request_id]
                            }
                            onClick={() => void handleFulfil(request.request_id)}
                            type="button"
                          >
                            {actionLoading === `fulfil-${request.request_id}`
                              ? "Fulfilling..."
                              : "Fulfil"}
                          </Button>
                          <Button
                            disabled={actionLoading === `decline-${request.request_id}`}
                            onClick={() => void handleDecline(request.request_id)}
                            type="button"
                            variant="outline"
                          >
                            {actionLoading === `decline-${request.request_id}`
                              ? "Declining..."
                              : "Decline"}
                          </Button>
                        </div>
                        {publishedProducts.length === 0 ? (
                          <p className="text-caption text-muted-foreground">
                            Publish a footprint before you can fulfil requests.
                          </p>
                        ) : null}
                      </div>
                    ) : null}

                    {shareLink ? (
                      <div className="space-y-2 rounded-lg border p-3">
                        <p className="text-small font-medium">Share link</p>
                        <p className="break-all text-caption text-muted-foreground">{shareLink}</p>
                        <Button
                          onClick={() => void copyLink(shareLink)}
                          size="sm"
                          type="button"
                          variant="outline"
                        >
                          <Copy className="h-4 w-4" />
                          Copy link
                        </Button>
                      </div>
                    ) : null}
                  </CardContent>
                </Card>
              );
            })
          )}

          {openRequests.length === 0 && requests.length > 0 ? (
            <p className="text-small text-muted-foreground">
              All requests have been fulfilled or declined.
            </p>
          ) : null}
        </div>
      )}
    </div>
  );
}
