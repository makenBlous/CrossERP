import { approvalTypes, autonomyPolicies, departments, documentLinks, suggestions } from '@/mocks/services/foundation-seed'
import type { ApprovalCardPayload, ChannelMessage, ChannelPlugin, ModuleSwitch } from '@/types/foundation'
import { moduleRegistry } from '@/config/permissions'

const fakeChannel = (id: string, nameZh: string, nameEn: string): ChannelPlugin => ({
  id,
  nameZh,
  nameEn,
  capabilities: { sendMessage: true, approvalCard: id !== 'email', verifyCallback: id !== 'email', bindIdentity: id !== 'webhook' },
  async sendMessage(_message: ChannelMessage) {
    return { ok: true, messageId: `${id}-msg-001` }
  },
  async sendApprovalCard(_card: ApprovalCardPayload) {
    return { ok: true, messageId: `${id}-approval-001` }
  },
  verifyCallback(payload: string, signature: string) {
    return payload.length > 0 && signature === `demo-${id}-signature`
  },
  async bindIdentity(externalAccount: string, userId: string) {
    return { ok: Boolean(externalAccount && userId), bindingId: `${id}-${userId}` }
  },
})

export const channelPlugins: ChannelPlugin[] = [
  fakeChannel('feishu', '飞书', 'Feishu'),
  fakeChannel('wecom', '企业微信', 'WeCom'),
  fakeChannel('dingtalk', '钉钉', 'DingTalk'),
  fakeChannel('email', '邮件', 'Email'),
  fakeChannel('webhook', 'Webhook', 'Webhook'),
]

export { approvalTypes, autonomyPolicies, departments, documentLinks, suggestions }
export const modules: ModuleSwitch[] = [...moduleRegistry]

