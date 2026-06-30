import AppShell from '@/components/AppShell';
import ControlledFailureBanner from '@/components/ControlledFailureBanner';
import PageHeader from '@/components/PageHeader';
import SectionCard from '@/components/SectionCard';
import ThemeSettings from '@/components/ThemeSettings';

export default function Settings() {
  return (
    <AppShell pageTitle="Settings">
      <div className="space-y-6">
        <PageHeader
          title="Settings"
          description="Local Command Center appearance preferences. These settings affect the frontend only and do not trigger backend workflows."
        />
        <SectionCard title="Theme settings" description="Persisted locally in this browser.">
          <ThemeSettings />
        </SectionCard>
        <ControlledFailureBanner title="Read-only settings scope">
          Runtime backend configuration, strategy approval, export, AI repair, Discord messaging, and
          live trading controls are outside Prompt 3.
        </ControlledFailureBanner>
      </div>
    </AppShell>
  );
}
