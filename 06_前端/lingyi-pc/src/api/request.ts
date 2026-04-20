export interface ApiResponse<T> {
  code: string
  message: string
  data: T
}

export interface DownloadFileResult {
  blob: Blob
  filename: string
  contentType: string
}

const buildAuthHeaders = (headers?: HeadersInit): Headers => {
  return new Headers(headers)
}

const parsePayload = async <T>(response: Response): Promise<ApiResponse<T> | null> => {
  try {
    return (await response.json()) as ApiResponse<T>
  } catch {
    return null
  }
}

const parseFilename = (disposition: string | null, fallback: string): string => {
  if (!disposition) return fallback
  const utf8Match = disposition.match(/filename\\*=UTF-8''([^;]+)/i)
  if (utf8Match?.[1]) {
    try {
      return decodeURIComponent(utf8Match[1])
    } catch {
      return utf8Match[1]
    }
  }
  const simpleMatch = disposition.match(/filename=\"?([^\";]+)\"?/i)
  return simpleMatch?.[1] || fallback
}

const sanitizeFilename = (filename: string, fallback: string): string => {
  const trimmed = filename.trim()
  if (!trimmed) return fallback
  const sanitized = trimmed
    .replace(/[\\/:*?"<>|\u0000-\u001f]/g, '_')
    .replace(/\s+/g, ' ')
    .trim()
  return sanitized || fallback
}

export const request = async <T>(url: string, init?: RequestInit): Promise<ApiResponse<T>> => {
  const response = await fetch(url, {
    ...init,
    credentials: 'include',
    headers: buildAuthHeaders(init?.headers),
  })

  const payload = await parsePayload<T>(response)

  if (response.status === 401 || payload?.code === 'AUTH_UNAUTHORIZED') {
    throw new Error('登录已失效，请重新登录')
  }
  if (response.status === 403 || payload?.code === 'AUTH_FORBIDDEN') {
    throw new Error('无权执行该操作')
  }
  if (
    response.status === 503 ||
    payload?.code === 'PERMISSION_SOURCE_UNAVAILABLE' ||
    payload?.code === 'ERPNEXT_SERVICE_UNAVAILABLE'
  ) {
    throw new Error(payload?.message || '服务暂不可用，请稍后重试')
  }
  if (!payload) {
    throw new Error(response.ok ? '响应格式错误' : '请求失败')
  }
  if (!response.ok || payload.code !== '0') {
    throw new Error(payload.message || '请求失败')
  }
  return payload
}

export const requestFile = async (
  url: string,
  init?: RequestInit,
  fallbackFilename = 'download.bin',
): Promise<DownloadFileResult> => {
  const response = await fetch(url, {
    ...init,
    credentials: 'include',
    headers: buildAuthHeaders(init?.headers),
  })

  if (!response.ok) {
    const payload = await parsePayload<unknown>(response)
    if (response.status === 401 || payload?.code === 'AUTH_UNAUTHORIZED') {
      throw new Error('登录已失效，请重新登录')
    }
    if (response.status === 403 || payload?.code === 'AUTH_FORBIDDEN') {
      throw new Error('无权执行该操作')
    }
    if (
      response.status === 503 ||
      payload?.code === 'PERMISSION_SOURCE_UNAVAILABLE' ||
      payload?.code === 'ERPNEXT_SERVICE_UNAVAILABLE'
    ) {
      throw new Error(payload?.message || '服务暂不可用，请稍后重试')
    }
    throw new Error(payload?.message || '请求失败')
  }

  const blob = await response.blob()
  const contentType = response.headers.get('content-type') || 'application/octet-stream'
  const parsedFilename = parseFilename(response.headers.get('content-disposition'), fallbackFilename)
  const filename = sanitizeFilename(parsedFilename, fallbackFilename)

  return { blob, filename, contentType }
}
