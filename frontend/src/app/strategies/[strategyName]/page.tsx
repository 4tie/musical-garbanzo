import StrategyDetailClient from './StrategyDetailClient';

interface StrategyDetailPageProps {
  params: Promise<{ strategyName: string }>;
}

export default async function StrategyDetailPage({ params }: StrategyDetailPageProps) {
  const { strategyName } = await params;

  return <StrategyDetailClient strategyName={decodeURIComponent(strategyName)} />;
}
