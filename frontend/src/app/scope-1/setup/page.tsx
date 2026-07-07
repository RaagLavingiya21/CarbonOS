"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { ArrowLeft } from "lucide-react";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  scope1Api,
  type S1ConsolidationPreview,
  type S1Entity,
  type S1Facility,
  type S1Inventory,
  type S1Source,
} from "@/lib/scope1-api";

const ENTITY_TYPES = [
  "parent",
  "wholly_owned_subsidiary",
  "majority_subsidiary",
  "joint_venture",
  "jointly_controlled_operation",
  "associate",
  "leased_asset_entity",
];
const APPROACHES = ["equity_share", "financial_control", "operational_control"];
const CATEGORIES = ["stationary_combustion", "mobile_combustion"];
const FUELS = [
  "natural_gas",
  "diesel_no2",
  "propane",
  "residual_oil_no6",
  "motor_gasoline",
  "diesel",
  "lpg",
  "cng",
  "lng",
];

function labelFor(value: string): string {
  return value.replace(/_/g, " ");
}

function TextField({
  label,
  value,
  onChange,
  type = "text",
  placeholder,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  type?: string;
  placeholder?: string;
}) {
  return (
    <div className="space-y-1.5">
      <Label>{label}</Label>
      <Input
        type={type}
        value={value}
        placeholder={placeholder}
        onChange={(event) => onChange(event.target.value)}
      />
    </div>
  );
}

function SelectField({
  label,
  value,
  onChange,
  options,
  placeholder,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  options: { value: string; label: string }[];
  placeholder?: string;
}) {
  return (
    <div className="space-y-1.5">
      <Label>{label}</Label>
      <select
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="h-9 w-full rounded-md border bg-card px-3 text-small"
      >
        <option value="">{placeholder ?? "Select…"}</option>
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </div>
  );
}

export default function Scope1SetupPage() {
  const [entities, setEntities] = useState<S1Entity[]>([]);
  const [facilities, setFacilities] = useState<S1Facility[]>([]);
  const [sources, setSources] = useState<S1Source[]>([]);
  const [inventories, setInventories] = useState<S1Inventory[]>([]);
  const [error, setError] = useState<string | null>(null);

  const reload = useCallback(async () => {
    try {
      const [e, f, s, i] = await Promise.all([
        scope1Api.listEntities(),
        scope1Api.listFacilities(),
        scope1Api.listSources(),
        scope1Api.listInventories(),
      ]);
      setEntities(e);
      setFacilities(f);
      setSources(s);
      setInventories(i);
    } catch (err) {
      setError((err as Error).message);
    }
  }, []);

  useEffect(() => {
    void reload();
  }, [reload]);

  const entityOptions = entities.map((e) => ({ value: e.id, label: e.name }));

  return (
    <div className="space-y-6">
      <Button asChild variant="ghost" className="-ml-3">
        <Link href="/scope-1">
          <ArrowLeft className="h-4 w-4" />
          Back to Scope 1
        </Link>
      </Button>

      <div>
        <h1 className="text-h1">Set up inventory</h1>
        <p className="mt-2 text-small text-muted-foreground">
          Model your organization, then declare a reporting-year inventory and register sources.
        </p>
      </div>

      {error ? (
        <Alert variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      ) : null}

      <EntitySection entities={entities} onSaved={reload} onError={setError} />
      <FacilitySection
        facilities={facilities}
        entityOptions={entityOptions}
        onSaved={reload}
        onError={setError}
      />
      <InventorySection
        inventories={inventories}
        entities={entities}
        entityOptions={entityOptions}
        onSaved={reload}
        onError={setError}
      />
      <BaseYearSection inventories={inventories} onSaved={reload} onError={setError} />

      <OperationalMetricsSection inventories={inventories} onSaved={reload} onError={setError} />
      <SourceSection
        sources={sources}
        entityOptions={entityOptions}
        facilities={facilities}
        onSaved={reload}
        onError={setError}
      />
    </div>
  );
}

// --- Entities ---------------------------------------------------------------

function EntitySection({
  entities,
  onSaved,
  onError,
}: {
  entities: S1Entity[];
  onSaved: () => void;
  onError: (message: string) => void;
}) {
  const [name, setName] = useState("");
  const [jurisdiction, setJurisdiction] = useState("US");
  const [entityType, setEntityType] = useState("parent");
  const [equity, setEquity] = useState("100");
  const [finControl, setFinControl] = useState(true);
  const [opControl, setOpControl] = useState(true);
  const [saving, setSaving] = useState(false);

  async function submit() {
    if (!name.trim()) return;
    setSaving(true);
    try {
      await scope1Api.createEntity({
        name: name.trim(),
        jurisdiction: jurisdiction.trim().toUpperCase().slice(0, 2),
        entity_type: entityType,
        equity_pct: equity ? Number(equity) : null,
        has_financial_control: finControl,
        has_operational_control: opControl,
        effective_from: new Date().toISOString().slice(0, 10),
      });
      setName("");
      onSaved();
    } catch (err) {
      onError((err as Error).message);
    } finally {
      setSaving(false);
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Legal entities</CardTitle>
        <CardDescription>Your corporate structure — used to consolidate emissions.</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <TextField label="Name" value={name} onChange={setName} placeholder="Acme Manufacturing" />
          <TextField label="Jurisdiction" value={jurisdiction} onChange={setJurisdiction} placeholder="US" />
          <SelectField
            label="Type"
            value={entityType}
            onChange={setEntityType}
            options={ENTITY_TYPES.map((t) => ({ value: t, label: labelFor(t) }))}
          />
          <TextField label="Equity %" value={equity} onChange={setEquity} type="number" />
        </div>
        <div className="flex flex-wrap items-center gap-4">
          <label className="flex items-center gap-2 text-small">
            <input type="checkbox" checked={finControl} onChange={(e) => setFinControl(e.target.checked)} />
            Financial control
          </label>
          <label className="flex items-center gap-2 text-small">
            <input type="checkbox" checked={opControl} onChange={(e) => setOpControl(e.target.checked)} />
            Operational control
          </label>
          <Button type="button" onClick={submit} disabled={saving || !name.trim()}>
            Add entity
          </Button>
        </div>
        <EntityList entities={entities} />
      </CardContent>
    </Card>
  );
}

function EntityList({ entities }: { entities: S1Entity[] }) {
  if (entities.length === 0) {
    return <p className="text-small text-muted-foreground">No entities yet.</p>;
  }
  return (
    <ul className="divide-y rounded-lg border">
      {entities.map((e) => (
        <li key={e.id} className="flex items-center justify-between px-3 py-2 text-small">
          <span className="font-medium">{e.name}</span>
          <span className="text-muted-foreground">
            {labelFor(e.entity_type)} · {e.jurisdiction} · equity {e.equity_pct ?? "—"}%
          </span>
        </li>
      ))}
    </ul>
  );
}

// --- Facilities -------------------------------------------------------------

function FacilitySection({
  facilities,
  entityOptions,
  onSaved,
  onError,
}: {
  facilities: S1Facility[];
  entityOptions: { value: string; label: string }[];
  onSaved: () => void;
  onError: (message: string) => void;
}) {
  const [entityId, setEntityId] = useState("");
  const [name, setName] = useState("");
  const [city, setCity] = useState("");
  const [saving, setSaving] = useState(false);

  async function submit() {
    if (!entityId || !name.trim()) return;
    setSaving(true);
    try {
      await scope1Api.createFacility({ entity_id: entityId, name: name.trim(), city: city.trim() || null });
      setName("");
      setCity("");
      onSaved();
    } catch (err) {
      onError((err as Error).message);
    } finally {
      setSaving(false);
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Facilities</CardTitle>
        <CardDescription>Sites under an entity where combustion sources live.</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid gap-3 sm:grid-cols-3">
          <SelectField label="Entity" value={entityId} onChange={setEntityId} options={entityOptions} />
          <TextField label="Name" value={name} onChange={setName} placeholder="Plant A" />
          <TextField label="City" value={city} onChange={setCity} />
        </div>
        <Button type="button" onClick={submit} disabled={saving || !entityId || !name.trim()}>
          Add facility
        </Button>
        {facilities.length === 0 ? (
          <p className="text-small text-muted-foreground">No facilities yet.</p>
        ) : (
          <ul className="divide-y rounded-lg border">
            {facilities.map((f) => (
              <li key={f.id} className="px-3 py-2 text-small font-medium">
                {f.name}
                {f.city ? <span className="text-muted-foreground"> · {f.city}</span> : null}
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}

// --- Inventory + consolidation preview --------------------------------------

function InventorySection({
  inventories,
  entities,
  entityOptions,
  onSaved,
  onError,
}: {
  inventories: S1Inventory[];
  entities: S1Entity[];
  entityOptions: { value: string; label: string }[];
  onSaved: () => void;
  onError: (message: string) => void;
}) {
  const year = new Date().getFullYear() - 1;
  const [reportingEntity, setReportingEntity] = useState("");
  const [reportingYear, setReportingYear] = useState(String(year));
  const [approach, setApproach] = useState("operational_control");
  const [baseYear, setBaseYear] = useState(String(year));
  const [saving, setSaving] = useState(false);
  const [previewEntity, setPreviewEntity] = useState("");
  const [preview, setPreview] = useState<S1ConsolidationPreview | null>(null);

  async function runPreview() {
    const entity = entities.find((e) => e.id === previewEntity);
    if (!entity) return;
    try {
      const result = await scope1Api.consolidationPreview({
        approach,
        equity_pct: entity.equity_pct ?? null,
        economic_interest_pct: entity.economic_interest_pct ?? null,
        has_financial_control: entity.has_financial_control ?? false,
        has_operational_control: entity.has_operational_control ?? false,
        entity_type: entity.entity_type,
      });
      setPreview(result);
    } catch (err) {
      onError((err as Error).message);
    }
  }

  async function submit() {
    if (!reportingEntity) return;
    setSaving(true);
    try {
      await scope1Api.createInventory({
        reporting_entity_id: reportingEntity,
        reporting_year: Number(reportingYear),
        period_start: `${reportingYear}-01-01`,
        period_end: `${reportingYear}-12-31`,
        consolidation_approach: approach,
        base_year: Number(baseYear),
      });
      onSaved();
    } catch (err) {
      onError((err as Error).message);
    } finally {
      setSaving(false);
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Reporting-year inventory</CardTitle>
        <CardDescription>
          One consolidation approach per inventory — applied to every entity, immutable once set.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <SelectField label="Reporting entity" value={reportingEntity} onChange={setReportingEntity} options={entityOptions} />
          <TextField label="Reporting year" value={reportingYear} onChange={setReportingYear} type="number" />
          <SelectField
            label="Consolidation approach"
            value={approach}
            onChange={setApproach}
            options={APPROACHES.map((a) => ({ value: a, label: labelFor(a) }))}
            placeholder="Select approach"
          />
          <TextField label="Base year" value={baseYear} onChange={setBaseYear} type="number" />
        </div>
        <Button type="button" onClick={submit} disabled={saving || !reportingEntity}>
          Create inventory
        </Button>

        <div className="rounded-lg border bg-secondary/40 p-3">
          <p className="text-small font-medium">Consolidation multiplier preview</p>
          <p className="text-caption text-muted-foreground">
            See how the chosen approach treats a given entity before you commit.
          </p>
          <div className="mt-2 flex flex-wrap items-end gap-3">
            <div className="min-w-48 flex-1">
              <SelectField label="Entity" value={previewEntity} onChange={setPreviewEntity} options={entityOptions} />
            </div>
            <Button type="button" variant="outline" onClick={runPreview} disabled={!previewEntity}>
              Preview
            </Button>
          </div>
          {preview ? (
            <p className="mt-2 text-small">
              <span className="font-semibold tabular-nums">{preview.multiplier.toFixed(4)}</span>
              <span className="text-muted-foreground"> — {preview.rationale}</span>
            </p>
          ) : null}
        </div>

        {inventories.length > 0 ? (
          <ul className="divide-y rounded-lg border">
            {inventories.map((inv) => (
              <li key={inv.id} className="flex items-center justify-between px-3 py-2 text-small">
                <span className="font-medium">{inv.reporting_year}</span>
                <span className="text-muted-foreground">
                  {labelFor(inv.consolidation_approach)} · {inv.status}
                  {inv.locked ? " · locked" : ""}
                </span>
              </li>
            ))}
          </ul>
        ) : null}
      </CardContent>
    </Card>
  );
}

// --- Base year (incumbent import) -------------------------------------------

function BaseYearSection({
  inventories,
  onSaved,
  onError,
}: {
  inventories: S1Inventory[];
  onSaved: () => void;
  onError: (message: string) => void;
}) {
  const [inventoryId, setInventoryId] = useState("");
  const [baseYear, setBaseYear] = useState("");
  const [total, setTotal] = useState("");
  const [gwp, setGwp] = useState("AR5");
  const [saving, setSaving] = useState(false);

  const options = inventories.map((inv) => ({ value: inv.id, label: String(inv.reporting_year) }));

  async function saveManual() {
    if (!inventoryId || !baseYear || !total) return;
    setSaving(true);
    try {
      await scope1Api.setBaseYear(inventoryId, {
        base_year: Number(baseYear),
        base_year_total_tco2e: Number(total),
        base_year_gwp_version: gwp,
      });
      onSaved();
    } catch (err) {
      onError((err as Error).message);
    } finally {
      setSaving(false);
    }
  }

  async function importCsv(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file || !inventoryId) return;
    try {
      await scope1Api.importBaseYear(inventoryId, file);
      onSaved();
    } catch (err) {
      onError((err as Error).message);
    } finally {
      event.target.value = "";
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Base year (migrate off a consultant / spreadsheet)</CardTitle>
        <CardDescription>
          Set the prior-year total that anchors your base year — enter it, or import a CSV
          (columns: base_year, total_tco2e, gwp_version). The file is kept as evidence.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <SelectField label="Inventory" value={inventoryId} onChange={setInventoryId} options={options} />
          <TextField label="Base year" value={baseYear} onChange={setBaseYear} type="number" />
          <TextField label="Prior-year total (tCO₂e)" value={total} onChange={setTotal} type="number" />
          <SelectField
            label="GWP version"
            value={gwp}
            onChange={setGwp}
            options={["AR4", "AR5", "AR6"].map((v) => ({ value: v, label: v }))}
          />
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <Button type="button" onClick={saveManual} disabled={saving || !inventoryId || !baseYear || !total}>
            Set base year
          </Button>
          <label className="text-small text-muted-foreground">
            or import CSV:
            <input type="file" accept=".csv" onChange={importCsv} disabled={!inventoryId} className="ml-2 text-small" />
          </label>
        </div>
      </CardContent>
    </Card>
  );
}

function OperationalMetricsSection({
  inventories,
  onSaved,
  onError,
}: {
  inventories: S1Inventory[];
  onSaved: () => void;
  onError: (message: string) => void;
}) {
  const [inventoryId, setInventoryId] = useState("");
  const [revenue, setRevenue] = useState("");
  const [currency, setCurrency] = useState("USD");
  const [output, setOutput] = useState("");
  const [outputUnit, setOutputUnit] = useState("");
  const [headcount, setHeadcount] = useState("");
  const [saving, setSaving] = useState(false);

  const options = inventories.map((inv) => ({ value: inv.id, label: String(inv.reporting_year) }));
  const ready = inventoryId && (revenue || output || headcount);

  async function save() {
    if (!ready) return;
    setSaving(true);
    try {
      await scope1Api.setInventoryMetrics(inventoryId, {
        ...(revenue ? { annual_revenue: Number(revenue), revenue_currency: currency } : {}),
        ...(output ? { output_quantity: Number(output), output_unit: outputUnit || null } : {}),
        ...(headcount ? { headcount: Number(headcount) } : {}),
      });
      onSaved();
    } catch (err) {
      onError((err as Error).message);
    } finally {
      setSaving(false);
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Operational metrics (for emissions intensity)</CardTitle>
        <CardDescription>
          Optional denominators used to compute intensity on the dashboard: tCO₂e per $M
          revenue, per output unit, and per employee. Set them per reporting year.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          <SelectField label="Inventory" value={inventoryId} onChange={setInventoryId} options={options} />
          <TextField label="Annual revenue" value={revenue} onChange={setRevenue} type="number" />
          <TextField label="Currency" value={currency} onChange={setCurrency} />
          <TextField label="Output quantity" value={output} onChange={setOutput} type="number" />
          <TextField label="Output unit" value={outputUnit} onChange={setOutputUnit} />
          <TextField label="Headcount (FTE)" value={headcount} onChange={setHeadcount} type="number" />
        </div>
        <Button type="button" onClick={save} disabled={saving || !ready}>
          Save metrics
        </Button>
      </CardContent>
    </Card>
  );
}

// --- Sources ----------------------------------------------------------------

function SourceSection({
  sources,
  entityOptions,
  facilities,
  onSaved,
  onError,
}: {
  sources: S1Source[];
  entityOptions: { value: string; label: string }[];
  facilities: S1Facility[];
  onSaved: () => void;
  onError: (message: string) => void;
}) {
  const [entityId, setEntityId] = useState("");
  const [facilityId, setFacilityId] = useState("");
  const [name, setName] = useState("");
  const [category, setCategory] = useState("stationary_combustion");
  const [fuel, setFuel] = useState("natural_gas");
  const [saving, setSaving] = useState(false);

  const facilityOptions = facilities
    .filter((f) => !entityId || f.entity_id === entityId)
    .map((f) => ({ value: f.id, label: f.name }));

  async function submit() {
    if (!entityId || !name.trim()) return;
    setSaving(true);
    try {
      await scope1Api.createSource({
        entity_id: entityId,
        facility_id: facilityId || null,
        source_name: name.trim(),
        source_category: category,
        primary_fuel: fuel,
      });
      setName("");
      onSaved();
    } catch (err) {
      onError((err as Error).message);
    } finally {
      setSaving(false);
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Combustion sources</CardTitle>
        <CardDescription>Boilers, generators, and fleet vehicles that burn fuel.</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
          <SelectField label="Entity" value={entityId} onChange={setEntityId} options={entityOptions} />
          <SelectField label="Facility" value={facilityId} onChange={setFacilityId} options={facilityOptions} placeholder="Optional" />
          <TextField label="Name" value={name} onChange={setName} placeholder="Boiler 1" />
          <SelectField
            label="Category"
            value={category}
            onChange={setCategory}
            options={CATEGORIES.map((c) => ({ value: c, label: labelFor(c) }))}
          />
          <SelectField label="Primary fuel" value={fuel} onChange={setFuel} options={FUELS.map((f) => ({ value: f, label: labelFor(f) }))} />
        </div>
        <Button type="button" onClick={submit} disabled={saving || !entityId || !name.trim()}>
          Register source
        </Button>
        {sources.length === 0 ? (
          <p className="text-small text-muted-foreground">No sources yet.</p>
        ) : (
          <ul className="divide-y rounded-lg border">
            {sources.map((s) => (
              <li key={s.id} className="flex items-center justify-between px-3 py-2 text-small">
                <span className="font-medium">{s.source_name}</span>
                <span className="text-muted-foreground">
                  {labelFor(s.source_category)}
                  {s.primary_fuel ? ` · ${labelFor(s.primary_fuel)}` : ""}
                  {s.is_excluded ? " · excluded" : ""}
                </span>
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}
