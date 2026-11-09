import { readMock } from '@/api/mock-client'
import { approvals } from '@/mocks/approvals'

export function fetchApprovals() {
  return readMock(approvals)
}
