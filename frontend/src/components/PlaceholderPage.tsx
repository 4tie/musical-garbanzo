import AppShell from './AppShell';
import ControlledFailureBanner from './ControlledFailureBanner';
import EmptyState from './EmptyState';
import PageHeader from './PageHeader';
import SectionCard from './SectionCard';

interface PlaceholderPageProps {
  title: string;
  description: string;
  focus: string;
}

export default function PlaceholderPage({ title, description, focus }: PlaceholderPageProps) {
  return (
    <AppShell pageTitle={title}>
      <div className="space-y-6">
        <PageHeader title={title} description={description} />
        <ControlledFailureBanner title="Read-only inspection mode">
          Real API data arrives in later prompts. This page does not show fake metrics, invent runs, trigger pipelines, approve strategies, export files, or offer live trading actions. No live trading actions exist in this dashboard.
        </ControlledFailureBanner>
        <SectionCard title={focus} description="The Command Center shell and UI primitives are ready.">
          <EmptyState
            title="No dashboard data rendered in this prompt"
            description="This placeholder intentionally waits for the next prompts to connect real backend evidence through the Part 09 API client."
          />
        </SectionCard>
      </div>
    </AppShell>
  );
}
