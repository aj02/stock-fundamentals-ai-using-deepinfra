'use client';

import { motion } from 'framer-motion';

import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { ThesisCard } from './thesis-card';
import { FinancialsSection } from './financials-section';
import { ValuationSection } from './valuation-section';
import { ManagementSection } from './management-section';
import { RiskSection } from './risk-section';
import type { RunReport } from '@/lib/schema';

export function ReportTabs({ report, animate = false }: { report: RunReport; animate?: boolean }) {
  const sections = [
    { key: 'overview', label: 'Overview', available: true },
    { key: 'financials', label: 'Financials', available: !!report.financials },
    { key: 'valuation', label: 'Valuation', available: !!report.valuation },
    { key: 'management', label: 'Management', available: !!report.management },
    { key: 'risk', label: 'Risks', available: !!report.risk },
    { key: 'thesis', label: 'Thesis', available: !!report.thesis },
    { key: 'raw', label: 'Raw JSON', available: true },
  ];

  return (
    <Tabs defaultValue="overview" className="w-full">
      <TabsList className="flex flex-wrap h-auto gap-1 p-1">
        {sections.map((s) => (
          <TabsTrigger
            key={s.key}
            value={s.key}
            disabled={!s.available}
            className="data-[state=active]:bg-[color:var(--color-card)]"
          >
            {s.label}
            {!s.available && (
              <Badge variant="outline" className="ml-2 text-[10px]">
                n/a
              </Badge>
            )}
          </TabsTrigger>
        ))}
      </TabsList>

      <TabsContent value="overview">
        <Overview report={report} animate={animate} />
      </TabsContent>
      <TabsContent value="financials">
        {report.financials && <FinancialsSection report={report.financials} />}
      </TabsContent>
      <TabsContent value="valuation">
        {report.valuation && <ValuationSection report={report.valuation} />}
      </TabsContent>
      <TabsContent value="management">
        {report.management && <ManagementSection report={report.management} />}
      </TabsContent>
      <TabsContent value="risk">
        {report.risk && <RiskSection report={report.risk} />}
      </TabsContent>
      <TabsContent value="thesis">
        {report.thesis && <ThesisCard thesis={report.thesis} animate={animate} />}
      </TabsContent>
      <TabsContent value="raw">
        <Card>
          <CardContent className="p-5">
            <pre className="overflow-x-auto rounded-md bg-[color:var(--color-muted)] p-4 text-xs">
              {JSON.stringify(report, null, 2)}
            </pre>
          </CardContent>
        </Card>
      </TabsContent>
    </Tabs>
  );
}

function Overview({ report, animate }: { report: RunReport; animate: boolean }) {
  return (
    <motion.div
      initial={animate ? { opacity: 0, y: 8 } : false}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25, ease: 'easeOut' }}
      className="space-y-6"
    >
      {report.thesis && <ThesisCard thesis={report.thesis} animate={animate} />}
      {report.unavailable_sections.length > 0 && (
        <Card>
          <CardContent className="p-5 text-sm">
            <h3 className="mb-2 text-sm font-semibold">Unavailable sections</h3>
            <ul className="space-y-1 text-xs text-[color:var(--color-muted-foreground)]">
              {report.unavailable_sections.map((u) => (
                <li key={u.section}>
                  <span className="font-medium capitalize text-[color:var(--color-foreground)]">{u.section}</span>: {u.reason}
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}
    </motion.div>
  );
}
