import { apiOperationRequest } from '@/shared/api/httpClient'

export const performanceApi = {
  summary() {
    return apiOperationRequest('progress_performance_retrieve', '/progress/performance/')
  },
}
