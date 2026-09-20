const BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000';

export async function fetchApi<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const url = `${BASE_URL}${endpoint}`;
  
  const headers = new Headers(options?.headers);
  if (!headers.has('Content-Type') && !(options?.body instanceof FormData)) {
    headers.set('Content-Type', 'application/json');
  }

  const response = await fetch(url, {
    ...options,
    headers,
  });

  if (!response.ok) {
    let errorData = null;
    let errorDetail = 'An error occurred';
    try {
      errorData = await response.json();
      errorDetail = errorData?.error?.message || errorDetail;
    } catch {
      // ignored
    }
    
    const error = new Error(errorDetail) as any;
    error.status = response.status;
    error.data = errorData;
    throw error;
  }
  
  return response.json();
}
