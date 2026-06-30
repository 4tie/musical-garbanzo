import OptimizationDetailClient from './OptimizationDetailClient';

interface OptimizationDetailProps {
  params: Promise<{ optimizationRunId: string }>;
}

export default async function OptimizationDetail({ params }: OptimizationDetailProps) {
  const { optimizationRunId } = await params;

  return <OptimizationDetailClient optimizationRunId={optimizationRunId} />;
}
