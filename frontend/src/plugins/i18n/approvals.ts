export const approvalsMessages = {
  'zh-CN': { title: '待我审批', submitted: '我提交的', detail: '审批详情', workflows: '流程配置', pending: '待审批', approved: '已通过', rejected: '已驳回', approve: '批准', reject: '驳回', comment: '审批意见', hash: '内容哈希', readonly: '当前角色只能查看，不能审批。', own: '不能审批自己的提交。', later: '多级审批为后期功能。' },
  'en': { title: 'To approve', submitted: 'Submitted by me', detail: 'Approval detail', workflows: 'Workflow setup', pending: 'Pending', approved: 'Approved', rejected: 'Rejected', approve: 'Approve', reject: 'Reject', comment: 'Comment', hash: 'Payload hash', readonly: 'This role can view but cannot decide.', own: 'You cannot approve your own submission.', later: 'Multi-step approval is planned for a later release.' },
} as const
