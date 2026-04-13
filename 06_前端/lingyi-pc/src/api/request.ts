export interface ApiResponse<T> {
  code: string
  message: string
  data: T
}

const buildAuthHeaders = (headers?: HeadersInit): Headers => {
  const result = new Headers(headers)
  const storedToken =
    window.localStorage.getItem('LY_AUTH_TOKEN') || window.localStorage.getItem('token') || ''
  if (storedToken) {
    const normalized =
      storedToken.startsWith('Bearer ') || storedToken.startsWith('token ')
        ? storedToken
        : `Bearer ${storedToken}`
    result.set('Authorization', normalized)
  }
  return result
}

const parsePayload = async <T>(response: Response): Promise<ApiResponse<T> | null> => {
  try {
    return (await response.json()) as ApiResponse<T>
  } catch {
    return null
  }
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
