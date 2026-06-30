"use client";

import {
  Alert,
  AlertDescription,
  AlertTitle,
} from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { AlertCircle, CheckCircle2, Info } from "lucide-react";

export default function StyleGuidePage() {
  return (
    <div className="bg-background min-h-screen py-12 px-4">
      <div className="max-w-4xl mx-auto space-y-12">
        {/* Header */}
        <div className="space-y-2">
          <h1 className="text-display font-display">Design System</h1>
          <p className="text-body text-muted-foreground">
            Visual reference for all UI primitives and design tokens.
          </p>
        </div>

        {/* Buttons */}
        <section className="space-y-6">
          <h2 className="text-h2 font-display">Buttons</h2>

          <div className="space-y-4">
            <div>
              <h3 className="text-h3 font-display mb-3">Variants</h3>
              <div className="flex flex-wrap gap-3 items-center">
                <Button variant="default">Default</Button>
                <Button variant="destructive">Destructive</Button>
                <Button variant="outline">Outline</Button>
                <Button variant="secondary">Secondary</Button>
                <Button variant="ghost">Ghost</Button>
                <Button variant="link">Link</Button>
              </div>
            </div>

            <div>
              <h3 className="text-h3 font-display mb-3">Sizes</h3>
              <div className="flex flex-wrap gap-3 items-center">
                <Button size="sm">Small</Button>
                <Button size="default">Default</Button>
                <Button size="lg">Large</Button>
                <Button size="icon">+</Button>
              </div>
            </div>

            <div>
              <h3 className="text-h3 font-display mb-3">States</h3>
              <div className="flex flex-wrap gap-3 items-center">
                <Button loading>Loading</Button>
                <Button disabled>Disabled</Button>
              </div>
            </div>
          </div>
        </section>

        {/* Badges */}
        <section className="space-y-6">
          <h2 className="text-h2 font-display">Badges</h2>
          <div className="flex flex-wrap gap-3 items-center">
            <Badge variant="default">Default</Badge>
            <Badge variant="secondary">Secondary</Badge>
            <Badge variant="destructive">Destructive</Badge>
            <Badge variant="outline">Outline</Badge>
            <Badge variant="low">Low 2.1</Badge>
            <Badge variant="medium">Medium 15.3</Badge>
            <Badge variant="high">High 45.8</Badge>
            <Badge variant="neutral">Neutral 8.2</Badge>
            <Badge variant="info">Info 92%</Badge>
          </div>
        </section>

        {/* Cards */}
        <section className="space-y-6">
          <h2 className="text-h2 font-display">Cards</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <Card>
              <CardHeader>
                <CardTitle>Card Title</CardTitle>
                <CardDescription>Card description goes here</CardDescription>
              </CardHeader>
              <CardContent>
                <p className="text-body">
                  This is an example card showing the basic layout and structure.
                </p>
              </CardContent>
              <CardFooter>
                <Button variant="secondary" size="sm">
                  Action
                </Button>
              </CardFooter>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Data Card</CardTitle>
                <CardDescription>Emission summary</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <p className="text-small text-muted-foreground">Total Emissions</p>
                  <p className="text-h2 font-display tabular-nums">
                    1,234.56 kg CO₂e
                  </p>
                </div>
              </CardContent>
            </Card>
          </div>
        </section>

        {/* Input */}
        <section className="space-y-6">
          <h2 className="text-h2 font-display">Input</h2>
          <div className="space-y-4 max-w-md">
            <div>
              <label className="text-small font-medium mb-2 block">
                Normal Input
              </label>
              <Input placeholder="Enter text..." />
            </div>
            <div>
              <label className="text-small font-medium mb-2 block">
                Disabled Input
              </label>
              <Input placeholder="Disabled..." disabled />
            </div>
            <div>
              <label className="text-small font-medium mb-2 block">
                Invalid Input
              </label>
              <Input
                placeholder="Error state..."
                aria-invalid={true}
              />
            </div>
          </div>
        </section>

        {/* Skeleton */}
        <section className="space-y-6">
          <h2 className="text-h2 font-display">Skeleton</h2>
          <div className="max-w-md space-y-3">
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-4/5" />
            <Skeleton className="h-32 w-full" />
          </div>
        </section>

        {/* Alerts */}
        <section className="space-y-6">
          <h2 className="text-h2 font-display">Alerts</h2>
          <div className="space-y-4 max-w-2xl">
            <Alert>
              <Info className="h-4 w-4" />
              <AlertTitle>Default Alert</AlertTitle>
              <AlertDescription>
                This is an informational alert message.
              </AlertDescription>
            </Alert>

            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertTitle>Destructive Alert</AlertTitle>
              <AlertDescription>
                This indicates an error or warning condition.
              </AlertDescription>
            </Alert>

            <Alert variant="success">
              <CheckCircle2 className="h-4 w-4" />
              <AlertTitle>Success Alert</AlertTitle>
              <AlertDescription>
                This indicates a successful operation or positive status.
              </AlertDescription>
            </Alert>
          </div>
        </section>

        {/* Typography */}
        <section className="space-y-6">
          <h2 className="text-h2 font-display">Typography</h2>
          <div className="space-y-4">
            <p className="text-display font-display">Display (3rem)</p>
            <h1 className="text-h1 font-display">Heading 1 (2.125rem)</h1>
            <h2 className="text-h2 font-display">Heading 2 (1.625rem)</h2>
            <h3 className="text-h3 font-display">Heading 3 (1.25rem)</h3>
            <p className="text-body-lg">Body Large (1.0625rem)</p>
            <p className="text-body">Body (0.9375rem)</p>
            <p className="text-small">Small (0.8125rem)</p>
            <p className="text-caption">Caption (0.75rem)</p>
            <p className="text-body tabular-nums">
              Tabular numbers: 1,234.56 kg CO₂e
            </p>
          </div>
        </section>

        {/* Data Palette */}
        <section className="space-y-6">
          <h2 className="text-h2 font-display">Data Palette</h2>
          <div className="flex flex-wrap gap-6">
            <div className="flex flex-col items-center gap-2">
              <div className="w-16 h-16 rounded-lg bg-data-low" />
              <p className="text-small font-medium">data-low</p>
            </div>
            <div className="flex flex-col items-center gap-2">
              <div className="w-16 h-16 rounded-lg bg-data-medium" />
              <p className="text-small font-medium">data-medium</p>
            </div>
            <div className="flex flex-col items-center gap-2">
              <div className="w-16 h-16 rounded-lg bg-data-high" />
              <p className="text-small font-medium">data-high</p>
            </div>
            <div className="flex flex-col items-center gap-2">
              <div className="w-16 h-16 rounded-lg bg-data-neutral" />
              <p className="text-small font-medium">data-neutral</p>
            </div>
            <div className="flex flex-col items-center gap-2">
              <div className="w-16 h-16 rounded-lg bg-data-info" />
              <p className="text-small font-medium">data-info</p>
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}
