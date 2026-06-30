import BaselineDetailClient from './BaselineDetailClient';

interface BaselineDetailProps {
  params: Promise<{ runId: string }>;
}

export default async function BaselineDetail({ params }: BaselineDetailProps) {
  const { runId } = await params;

  return <BaselineDetailClient runId={runId} />;
}
