import { apiOperationRequest } from '@/shared/api/httpClient'
import type { ApiRequestBody, ApiResponseBody } from '@/shared/api/generated/apiTypes'

export type AIChatRequest = ApiRequestBody<'ai_chat_create'>
export type AIChatResponse = ApiResponseBody<'ai_chat_create'>

export const aiSupportApi = {
  chat(payload: AIChatRequest) {
    return apiOperationRequest('ai_chat_create', '/ai/chat/', { body: payload })
  },
}
