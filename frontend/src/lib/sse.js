const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

export function connectToStream(queryId, handlers) {
  const url = `${BASE_URL}/queries/${queryId}/stream`;
  const eventSource = new EventSource(url);

  eventSource.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      if (handlers.onStep && data.event === 'step') {
        handlers.onStep(data);
      } else if (handlers.onComplete && data.event === 'complete') {
        handlers.onComplete(data);
      }
    } catch (err) {
      console.error('Failed to parse SSE event:', err);
    }
  };

  eventSource.addEventListener('step', (event) => {
    try {
      const data = JSON.parse(event.data);
      if (handlers.onStep) handlers.onStep(data);
    } catch (e) {
      console.error(e);
    }
  });

  eventSource.addEventListener('complete', (event) => {
    try {
      const data = JSON.parse(event.data);
      if (handlers.onComplete) handlers.onComplete(data);
    } catch (e) {
      console.error(e);
    }
  });

  const phase3Events = [
    'claim:extracted', 'claim:verified', 'claim:disputed',
    'contradiction:detected', 'contradiction:resolved',
    'source:scored', 'evidence:graph_updated'
  ];

  phase3Events.forEach(eventType => {
    eventSource.addEventListener(eventType, (event) => {
      try {
        const data = JSON.parse(event.data);
        if (handlers.onPhase3Event) handlers.onPhase3Event(eventType, data);
      } catch (e) {
        console.error(e);
      }
    });
  });

  eventSource.onerror = (err) => {
    if (handlers.onError) handlers.onError(err);
    eventSource.close();
  };

  return () => {
    eventSource.close();
  };
}
