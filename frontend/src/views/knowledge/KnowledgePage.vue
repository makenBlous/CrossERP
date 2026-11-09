<script setup lang="ts">
/* eslint-disable max-statements-per-line */
import { askOnboarding, createKbDocument, createKbFolder, createKbVersion, decideKbReview, downloadEmployeeFile, fetchEmployeeFiles, fetchKbAccessLogs, fetchKbDocument, fetchKbDocuments, fetchKbExpiring, fetchKbQa, fetchKbReviews, fetchKbSpace, fetchKbSpaces, fetchKbVersions, fetchOnboarding, rebuildKbIndex, renameKbFolder, saveKbSpaceMembers, saveOnboarding, searchKb, setKbSpaceFinanceOnly, submitKbDocument, suggestKbQa, uploadEmployeeFile, uploadKbAttachment } from '@/api/gap-e'
import TiptapEditor from '@core/components/TiptapEditor.vue'
import DetailPage from '@/components/biz/DetailPage.vue'
import FormDrawer from '@/components/biz/FormDrawer.vue'
import FormPage from '@/components/biz/FormPage.vue'
import ListPage from '@/components/biz/ListPage.vue'
import PermissionGate from '@/components/biz/PermissionGate.vue'
import RecordDrawer from '@/components/biz/RecordDrawer.vue'
import StatusChip from '@/components/biz/StatusChip.vue'
import { useAiModeStore } from '@/stores/ai-mode'
import { useSessionStore } from '@/stores/session'
import type { Role } from '@/types/domain'
import type { EmployeeFile, KbAccessLog, KbDocument, KbExpiryItem, KbFolder, KbQaItem, KbReviewItem, KbSearchResult, KbSpace, KbSpaceMember, KbVersion, OnboardingChecklistItem } from '@/types/gap-e'

type Mode = 'home' | 'doc' | 'space' | 'edit' | 'review' | 'qa' | 'expiring' | 'index' | 'access' | 'employee' | 'onboarding' | 'onboarding-admin'
const props = defineProps<{ mode: Mode }>()
const route = useRoute()
const router = useRouter()
const session = useSessionStore()
const aiMode = useAiModeStore()
const showAi = computed(() => aiMode.isEnabled)
const busy = ref(false)
const error = ref('')
const message = ref('')
const spaces = ref<KbSpace[]>([])
const documents = ref<KbDocument[]>([])
const document = ref<KbDocument | null>(null)
const space = ref<KbSpace | null>(null)
const versions = ref<KbVersion[]>([])
const reviews = ref<KbReviewItem[]>([])
const qa = ref<KbQaItem[]>([])
const expiring = ref<KbExpiryItem[]>([])
const results = ref<KbSearchResult[]>([])
const logs = ref<KbAccessLog[]>([])
const files = ref<EmployeeFile[]>([])
const onboarding = ref<OnboardingChecklistItem[]>([])
const indexVersion = ref(1)
const query = ref('')
const answer = ref<{ answer: string; citations: Array<{ label: string; href: string; docId: string; version: number }> } | null>(null)
const title = ref('')
const content = ref('')
const kind = ref('policy')
const tags = ref('')
const expiresOn = ref('')
const selectedSpace = ref('space-company')
const reviewReason = ref('')
const reviewOpen = ref(false)
const reviewTarget = ref<KbReviewItem | null>(null)
const reviewDecision = ref<'approve' | 'reject'>('reject')
const versionOpen = ref(false)
const selectedVersion = ref<KbVersion | null>(null)
const spaceSettingsOpen = ref(false)
const spaceFinanceOnlyDraft = ref(false)
const visibleRolesDraft = ref<Role[]>([])
const spaceMembersDraft = ref<KbSpaceMember[]>([])
const folderName = ref('')
const selectedFolder = ref<KbFolder | null>(null)
const renameName = ref('')
const memberRole = ref('operator')
const memberName = ref('')
const memberScope = ref<'read' | 'edit' | 'admin'>('read')
const qaOpen = ref(false)
const selectedQa = ref<KbQaItem | null>(null)
const accessOpen = ref(false)
const selectedAccess = ref<KbAccessLog | null>(null)
const fileOpen = ref(false)
const selectedFile = ref<EmployeeFile | null>(null)
const onboardingOpen = ref(false)
const onboardingDraft = ref<OnboardingChecklistItem | null>(null)
const onboardingRole = ref('purchaser')
const employeeFileKind = ref<EmployeeFile['kind']>('certificate')
const employeeUploadInput = ref<HTMLInputElement | null>(null)
const attachmentInput = ref<HTMLInputElement | null>(null)

const id = computed(() => String((route.params as Record<string, unknown>).id ?? ''))
const employeeId = computed(() => id.value || session.userId)
const onboardingProgress = computed(() => onboarding.value.length ? Math.round(onboarding.value.filter(item => item.done).length / onboarding.value.length * 100) : 0)

async function run(action: () => Promise<void>) {
  busy.value = true; error.value = ''; try { await action() }
  catch (e) { error.value = e instanceof Error ? e.message : '操作失败' }
  finally { busy.value = false }
}
async function load() {
  await run(async () => {
    if (props.mode === 'home' || props.mode === 'edit') { spaces.value = await fetchKbSpaces(); documents.value = await fetchKbDocuments() }
    if (props.mode === 'doc') {
      document.value = await fetchKbDocument(id.value); if (document.value)
        versions.value = await fetchKbVersions(id.value)
    }
    if (props.mode === 'edit' && id.value && id.value !== 'new') { document.value = await fetchKbDocument(id.value); if (document.value) { title.value = document.value.title; content.value = document.value.content; tags.value = document.value.tags.join(', '); kind.value = document.value.kind; expiresOn.value = document.value.expiresOn ?? ''; selectedSpace.value = document.value.spaceId } }
    if (props.mode === 'space') { space.value = await fetchKbSpace(id.value); documents.value = await fetchKbDocuments(id.value) }
    if (props.mode === 'review')
      reviews.value = await fetchKbReviews()
    if (props.mode === 'qa')
      qa.value = await fetchKbQa()
    if (props.mode === 'expiring')
      expiring.value = await fetchKbExpiring()
    if (props.mode === 'access')
      logs.value = await fetchKbAccessLogs()
    if (props.mode === 'employee')
      files.value = await fetchEmployeeFiles(employeeId.value)
    if (props.mode === 'onboarding')
      onboarding.value = await fetchOnboarding(session.role)
    if (props.mode === 'onboarding-admin')
      onboarding.value = await fetchOnboarding('purchaser')
  })
}
onMounted(load)
watch(() => props.mode, load)

async function search() {
  await run(async () => {
    results.value = await searchKb(query.value); if (!results.value.length)
      message.value = '当前权限范围内没有匹配的文档。'
  })
}
async function saveDraft() {
  await run(async () => {
    const created = await createKbDocument({ title: title.value, content: content.value, kind: kind.value as KbDocument['kind'], spaceId: selectedSpace.value, tags: tags.value.split(',').map(item => item.trim()).filter(Boolean), expiresOn: expiresOn.value || null })

    message.value = '草稿已保存，可提交审核。'; await router.push(`/kb/docs/${created.id}/edit`)
  })
}
async function submit() {
  if (!document.value)
    return; await run(async () => { document.value = await submitKbDocument(document.value!.id); message.value = '已提交空间管理员审核。' })
}
async function saveVersion() {
  if (!document.value)
    return; await run(async () => { document.value = await createKbVersion(document.value!.id, content.value); versions.value = await fetchKbVersions(document.value!.id); message.value = `第 ${document.value.currentVersion} 版已保存，请重新提交审核。` })
}
function openReview(item: KbReviewItem, decision: 'approve' | 'reject') {
  reviewTarget.value = item
  reviewDecision.value = decision
  reviewReason.value = ''
  reviewOpen.value = true
}
async function review() {
  if (!reviewTarget.value)
    return

  await run(async () => {
    await decideKbReview(reviewTarget.value!.id, reviewDecision.value, reviewReason.value)
    reviews.value = await fetchKbReviews()
    reviewOpen.value = false
    message.value = reviewDecision.value === 'approve' ? '已批准并发布。' : '已驳回并记录原因。'
  })
}
async function suggest() { await run(async () => { await suggestKbQa('ticket-1007'); message.value = '已生成建议问答并送入审核队列。' }) }
async function rebuild() { await run(async () => { indexVersion.value = await rebuildKbIndex(); message.value = `索引已重建（v${indexVersion.value}）。` }) }
async function searchIndex() { await run(async () => { results.value = await searchKb(query.value) }) }
function openSpaceSettings() {
  if (!space.value)
    return

  spaceFinanceOnlyDraft.value = space.value.financeOnly
  visibleRolesDraft.value = [...(space.value.visibleRoles ?? [])]
  spaceMembersDraft.value = [...(space.value.members ?? [])]
  spaceSettingsOpen.value = true
}
async function saveSpaceSettings() {
  if (!space.value)
    return

  await run(async () => {
    if (spaceFinanceOnlyDraft.value)
      visibleRolesDraft.value = ['finance']
    space.value = await saveKbSpaceMembers(space.value!.id, spaceMembersDraft.value, visibleRolesDraft.value)
    space.value = await setKbSpaceFinanceOnly(space.value!.id, spaceFinanceOnlyDraft.value)
    spaceSettingsOpen.value = false
    message.value = space.value?.financeOnly ? '已限制为仅财务可见。' : '已恢复空间成员可见。'
  })
}
async function download(file: EmployeeFile) { await run(async () => { await downloadEmployeeFile(employeeId.value, file.id); message.value = '下载记录已写入敏感文档访问日志。' }) }
async function uploadEmployee(event: Event) {
  const file = (event.target as HTMLInputElement).files?.[0]
  if (!file)
    return
  await run(async () => {
    const saved = await uploadEmployeeFile(employeeId.value, file, employeeFileKind.value)

    files.value.unshift(saved); message.value = '文件元数据已登记（模拟存储），上传审计已写入。'
  })
  if (employeeUploadInput.value)
    employeeUploadInput.value.value = ''
}
async function uploadAttachment(event: Event) {
  const file = (event.target as HTMLInputElement).files?.[0]
  if (!file || !document.value)
    return
  await run(async () => { document.value = await uploadKbAttachment(document.value!.id, file); message.value = '附件元数据已登记（模拟存储），上传审计已写入。' })
  if (attachmentInput.value)
    attachmentInput.value.value = ''
}
async function addFolder() {
  if (!space.value || !folderName.value.trim())
    return
  await run(async () => { await createKbFolder(space.value!.id, folderName.value); space.value = await fetchKbSpace(space.value!.id); folderName.value = ''; message.value = '文件夹已新增（模拟），并写入审计。' })
}
async function renameSelectedFolder() {
  if (!selectedFolder.value || !renameName.value.trim() || !space.value)
    return
  await run(async () => { await renameKbFolder(selectedFolder.value!.id, renameName.value); space.value = await fetchKbSpace(space.value!.id); renameName.value = ''; message.value = '文件夹已重命名（模拟），并写入审计。' })
}
function addMember() {
  if (!memberName.value.trim() || !space.value)
    return
  spaceMembersDraft.value.push({ id: `draft-${Date.now()}`, spaceId: space.value.id, name: memberName.value.trim(), role: memberRole.value as KbSpaceMember['role'], scope: memberScope.value })
  memberName.value = ''
}
async function ask() { await run(async () => { answer.value = await askOnboarding(query.value) }) }
async function saveItem(item: OnboardingChecklistItem) { await run(async () => { await saveOnboarding({ ...item }); message.value = '上手清单已保存。' }) }
function openVersion(version: KbVersion) { selectedVersion.value = version; versionOpen.value = true }
function openQa(item: KbQaItem) { selectedQa.value = item; qaOpen.value = true }
function openAccess(item: KbAccessLog) { selectedAccess.value = item; accessOpen.value = true }
function openFile(item: EmployeeFile) { selectedFile.value = item; fileOpen.value = true }
function editOnboarding(item: OnboardingChecklistItem) { onboardingDraft.value = { ...item }; onboardingRole.value = item.roleId; onboardingOpen.value = true }
function addOnboardingItem() { onboardingDraft.value = { id: `draft-${Date.now()}`, roleId: onboardingRole.value, title: '', description: '', route: '/dashboard', done: false }; onboardingOpen.value = true }
async function loadOnboardingRole(value: unknown) { onboardingRole.value = String(value); await run(async () => { onboarding.value = await fetchOnboarding(onboardingRole.value) }) }
async function saveOnboardingDraft() {
  if (!onboardingDraft.value)
    return

  await run(async () => {
    await saveOnboarding({ ...onboardingDraft.value! })
    onboarding.value = await fetchOnboarding(onboardingRole.value)
    onboardingOpen.value = false
    message.value = '上手清单已保存。'
  })
}
function openDoc(docId: string) { router.push(`/kb/docs/${docId}`) }
</script>

<template>
  <div>
    <VAlert
      v-if="showAi && ['home', 'doc', 'qa', 'index', 'onboarding'].includes(mode)"
      type="info"
      variant="tonal"
      class="mb-6"
    >
      AI 只提供带出处的建议或检索解释，不会修改金额或直接发布内容。建议动作仍需人工审核。
    </VAlert>
    <VAlert
      v-if="!showAi && ['home', 'doc', 'qa', 'index', 'onboarding'].includes(mode)"
      type="info"
      variant="tonal"
      class="mb-6"
    >
      AI 已关闭，页面仍可通过人工路径完成文档编辑、审核、检索和上手清单操作。
    </VAlert>
    <VAlert
      v-if="error"
      type="error"
      variant="tonal"
      class="mb-6"
    >
      {{ error }}
    </VAlert>
    <VAlert
      v-if="message"
      type="success"
      variant="tonal"
      closable
      class="mb-6"
      @click:close="message = ''"
    >
      {{ message }}
    </VAlert>

    <template v-if="mode === 'home'">
      <div class="d-flex justify-end mb-4">
        <PermissionGate action="create">
          <VBtn
            to="/kb/docs/new/edit"
            prepend-icon="tabler-plus"
          >
            新建制度文档
          </VBtn>
        </PermissionGate>
      </div>
      <ListPage
        storage-key="kb-home"
        title="知识库"
        subtitle="按空间权限检索制度、SOP 和经验。"
        :items="spaces"
        :columns="[{ key: 'name', title: '空间' }, { key: 'description', title: '说明' }, { key: 'memberCount', title: '成员数' }, { key: 'updatedAt', title: '最近更新' }]"
        @open="row => router.push(`/kb/spaces/${row.id}`)"
      >
        <template #widgets>
          <VRow class="mb-2">
            <VCol
              cols="12"
              md="4"
            >
              <KpiCard
                title="可访问空间"
                :value="String(spaces.length)"
                icon="tabler-books"
              />
            </VCol><VCol
              cols="12"
              md="4"
            >
              <KpiCard
                title="可检索文档"
                :value="String(documents.length)"
                icon="tabler-file-text"
              />
            </VCol><VCol
              cols="12"
              md="4"
            >
              <KpiCard
                title="索引状态"
                value="正常"
                icon="tabler-search"
              />
            </VCol>
          </VRow>
        </template>
      </ListPage>
      <VCard
        class="mt-6"
        title="全文搜索"
      >
        <VCardText>
          <div class="d-flex gap-3">
            <AppTextField
              v-model="query"
              label="搜索制度、SOP 或问答"
              class="flex-grow-1"
              @keyup.enter="search"
            /><VBtn
              :loading="busy"
              @click="search"
            >
              搜索
            </VBtn>
          </div><VList
            v-if="results.length"
            class="mt-4"
          >
            <VListItem
              v-for="item in results"
              :key="item.id"
              :title="item.title"
              :subtitle="`${item.spaceName} · v${item.version} · ${item.excerpt}`"
              @click="openDoc(item.docId)"
            />
          </VList>
        </VCardText>
      </VCard>
    </template>

    <template v-else-if="mode === 'doc'">
      <DetailPage
        v-if="document"
        :title="document.title"
        :subtitle="`${document.kind} · 版本 ${document.currentVersion}`"
        :status="document.status"
        domain="approval"
        :timeline="versions.map(version => ({ id: version.id, at: version.createdAt, title: `版本 v${version.version}`, detail: version.status, actor: version.author }))"
      >
        <template #actions>
          <PermissionGate action="update">
            <VBtn
              v-if="['draft', 'published'].includes(document.status)"
              :to="`/kb/docs/${document.id}/edit`"
              variant="tonal"
            >
              编辑
            </VBtn><VBtn
              v-if="document.status === 'draft'"
              :loading="busy"
              @click="submit"
            >
              提交审核
            </VBtn>
          </PermissionGate>
        </template>
        <VCard title="正文">
          <VCardText
            class="text-body-1"
            style="white-space: pre-wrap;"
          >
            {{ document.content }}
          </VCardText>
        </VCard>
        <VCard
          class="mt-6"
          title="标签与有效期"
        >
          <VCardText>
            <VChip
              v-for="tag in document.tags"
              :key="tag"
              class="me-2"
              color="primary"
              variant="tonal"
            >
              {{ tag }}
            </VChip><span
              v-if="document.expiresOn"
              class="ms-4"
            >有效期至 {{ document.expiresOn }}</span>
          </VCardText>
        </VCard>
        <VCard
          class="mt-6"
          title="附件（模拟存储）"
        >
          <VCardText>
            <VAlert
              type="info"
              variant="tonal"
              class="mb-4"
            >
              只登记文件名、类型、大小和上传人；真实文件不会上传。查看和下载动作会写审计。
            </VAlert>
            <VList
              v-if="document.attachments?.length"
              density="compact"
            >
              <VListItem
                v-for="attachment in document.attachments"
                :key="attachment.id"
                :title="attachment.fileName"
                :subtitle="`${attachment.contentType} · ${attachment.size} · ${attachment.uploadedBy}`"
              />
            </VList>
            <VBtn
              v-if="document.status === 'draft'"
              variant="tonal"
              prepend-icon="tabler-paperclip"
              @click="attachmentInput?.click()"
            >
              登记附件
            </VBtn>
            <input
              ref="attachmentInput"
              type="file"
              class="d-none"
              @change="uploadAttachment"
            >
          </VCardText>
        </VCard>
        <VCard
          class="mt-6"
          title="版本历史"
        >
          <ListPage
            embedded
            storage-key="kb-document-versions"
            title="版本历史"
            :items="versions"
            :columns="[{ key: 'version', title: '版本' }, { key: 'status', title: '状态' }, { key: 'author', title: '作者' }, { key: 'createdAt', title: '时间' }]"
            @open="openVersion"
          >
            <template #item.version="{ item }">
              v{{ item.version }}
            </template>
            <template #item.status="{ item }">
              <StatusChip
                domain="approval"
                :value="item.status"
              />
            </template>
          </ListPage>
        </VCard>
      </DetailPage>
      <RecordDrawer
        v-if="selectedVersion"
        v-model="versionOpen"
        title="版本内容"
      >
        <StatusChip
          domain="approval"
          :value="selectedVersion.status"
        />
        <p class="text-caption text-medium-emphasis mt-3">
          {{ selectedVersion.author }} · {{ selectedVersion.createdAt }}
        </p>
        <p
          class="mt-4"
          style="white-space: pre-wrap;"
        >
          {{ selectedVersion.content }}
        </p>
      </RecordDrawer>
    </template>

    <template v-else-if="mode === 'space'">
      <DetailPage
        v-if="space"
        :title="space.name"
        :subtitle="space.description"
      >
        <template #actions>
          <PermissionGate action="update">
            <VBtn
              variant="tonal"
              prepend-icon="tabler-lock"
              @click="openSpaceSettings"
            >
              管理空间权限
            </VBtn>
          </PermissionGate>
        </template><VCard title="空间权限">
          <VCardText>
            <VAlert
              :type="space.financeOnly ? 'warning' : 'info'"
              variant="tonal"
            >
              {{ space.financeOnly ? '运营和普通员工的搜索与 AI 引用都会被过滤。' : '当前空间对有权限的成员开放。' }}
            </VAlert>
          </VCardText>
        </VCard>
        <VCard
          class="mt-6"
          title="文件夹树与空间成员（模拟）"
        >
          <VCardText>
            <div class="d-flex flex-wrap gap-3 align-center mb-4">
              <AppTextField
                v-model="folderName"
                label="新文件夹名称"
                style="max-inline-size: 18rem;"
              />
              <VBtn
                prepend-icon="tabler-folder-plus"
                @click="addFolder"
              >
                新增文件夹
              </VBtn>
            </div>
            <VList
              density="compact"
              class="mb-4"
            >
              <VListItem
                v-for="folder in space.folders"
                :key="folder.id"
                :title="folder.name"
                prepend-icon="tabler-folder"
                @click="selectedFolder = folder; renameName = folder.name"
              >
                <template #append>
                  <VChip
                    v-if="selectedFolder?.id === folder.id"
                    size="small"
                    color="primary"
                    variant="tonal"
                  >
                    已选择
                  </VChip>
                </template>
              </VListItem>
            </VList>
            <div class="d-flex flex-wrap gap-3 align-center mb-4">
              <AppTextField
                v-model="renameName"
                label="重命名已选文件夹"
                style="max-inline-size: 18rem;"
              />
              <VBtn
                variant="tonal"
                :disabled="!selectedFolder"
                @click="renameSelectedFolder"
              >
                重命名
              </VBtn>
            </div>
            <VDivider class="my-4" />
            <div class="text-subtitle-2 mb-2">
              成员与可见范围
            </div>
            <div class="d-flex flex-wrap gap-3 align-center mb-3">
              <AppTextField
                v-model="memberName"
                label="成员名称"
                style="max-inline-size: 14rem;"
              />
              <AppSelect
                v-model="memberRole"
                label="角色"
                :items="[{ title: '运营', value: 'operator' }, { title: '财务', value: 'finance' }, { title: '普通员工', value: 'employee' }, { title: '审计', value: 'auditor' }]"
                style="max-inline-size: 12rem;"
              />
              <AppSelect
                v-model="memberScope"
                label="范围"
                :items="[{ title: '只读', value: 'read' }, { title: '可编辑', value: 'edit' }, { title: '空间管理员', value: 'admin' }]"
                style="max-inline-size: 12rem;"
              />
              <VBtn
                variant="tonal"
                @click="addMember"
              >
                添加成员
              </VBtn>
            </div>
            <VList density="compact">
              <VListItem
                v-for="member in spaceMembersDraft"
                :key="member.id"
                :title="member.name"
                :subtitle="`${member.role} · ${member.scope}`"
              />
            </VList>
          </VCardText>
        </VCard>
        <ListPage
          embedded
          storage-key="kb-space-documents"
          title="空间文档"
          :items="documents"
          :columns="[{ key: 'title', title: '文档' }, { key: 'kind', title: '类型' }, { key: 'status', title: '状态' }, { key: 'currentVersion', title: '版本' }, { key: 'updatedAt', title: '最近更新' }]"
          @open="row => openDoc(row.id)"
        >
          <template #item.status="{ item }">
            <StatusChip
              domain="approval"
              :value="item.status"
            />
          </template>
          <template #item.currentVersion="{ item }">
            v{{ item.currentVersion }}
          </template>
        </ListPage>
      </DetailPage>
      <FormDrawer
        v-model="spaceSettingsOpen"
        title="管理空间权限"
        :saving="busy"
        @save="saveSpaceSettings"
      >
        <VSwitch
          v-model="spaceFinanceOnlyDraft"
          label="仅财务可见"
          color="primary"
          hide-details
        />
        <VAlert
          type="info"
          variant="tonal"
          class="mt-4"
        >
          变更会记录审计，并同步影响文档列表和检索问答的权限过滤。
        </VAlert>
        <VCheckbox
          v-model="visibleRolesDraft"
          value="operator"
          label="运营可见"
          hide-details
        />
        <VCheckbox
          v-model="visibleRolesDraft"
          value="employee"
          label="普通员工可见"
          hide-details
        />
        <VCheckbox
          v-model="visibleRolesDraft"
          value="finance"
          label="财务可见"
          hide-details
        />
      </FormDrawer>
    </template>

    <template v-else-if="mode === 'edit'">
      <FormPage
        :title="document ? `编辑：${document.title}` : '新建制度文档'"
        subtitle="保存后提交空间管理员审核；发布动作始终需要人工确认。"
        :saving="busy"
        @save="document ? saveVersion() : saveDraft()"
        @cancel="router.push(document ? `/kb/docs/${document.id}` : '/kb')"
      >
        <template #default>
          <VAlert
            v-if="showAi"
            type="info"
            variant="tonal"
            class="mb-4"
          >
            AI 预填：可在右侧助手中请求摘要或标签建议，提交前请人工核对。
          </VAlert><AppTextField
            v-model="title"
            label="文档标题"
            :rules="[requiredValidator]"
            class="mb-4"
          /><AppSelect
            v-model="kind"
            label="文档类型"
            :items="[{ title: '制度', value: 'policy' }, { title: 'SOP', value: 'sop' }, { title: '帮助', value: 'help' }]"
            class="mb-4"
          /><AppSelect
            v-if="!document"
            v-model="selectedSpace"
            label="所属空间"
            :items="spaces.map(item => ({ title: item.name, value: item.id }))"
            class="mb-4"
          /><AppTextField
            v-model="tags"
            label="标签（逗号分隔）"
            class="mb-4"
          /><AppTextField
            v-model="expiresOn"
            label="有效期（可选）"
            placeholder="YYYY-MM-DD"
            class="mb-4"
          /><TiptapEditor
            v-model="content"
            placeholder="请输入制度、SOP 或帮助文档正文"
          />
        </template><template #aside>
          <VCard title="人工发布检查">
            <VCardText>
              <VCheckbox label="内容已核对" /><VCheckbox label="引用和附件已核对" /><VAlert
                type="warning"
                variant="tonal"
                class="mt-2"
              >
                保存只产生草稿，发布必须经过审核。
              </VAlert>
            </VCardText>
          </VCard>
        </template>
      </FormPage>
    </template>

    <template v-else-if="mode === 'review'">
      <ListPage
        storage-key="kb-review"
        title="发布审核"
        subtitle="文档和 AI 建议问答统一进入审核队列。"
        :items="reviews"
        :columns="[{ key: 'title', title: '待审内容' }, { key: 'type', title: '类型' }, { key: 'submittedBy', title: '提交人' }, { key: 'submittedAt', title: '提交时间' }, { key: 'status', title: '状态' }]"
      >
        <template #item.status="{ item }">
          <StatusChip
            domain="approval"
            :value="item.status"
          />
        </template><template #item.type="{ item }">
          <VChip
            size="small"
            variant="tonal"
          >
            {{ item.type === 'document' ? '文档' : '建议问答' }}
          </VChip>
        </template><template #item.title="{ item }">
          <div class="d-flex align-center gap-2">
            <span>{{ item.title }}</span><PermissionGate action="approve">
              <VBtn
                size="small"
                variant="text"
                @click.stop="openReview(item, 'approve')"
              >
                批准
              </VBtn><VBtn
                size="small"
                color="error"
                variant="text"
                @click.stop="openReview(item, 'reject')"
              >
                驳回
              </VBtn>
            </PermissionGate>
          </div>
        </template>
      </ListPage><VCard
        class="mt-6"
        title="驳回原因"
      >
        <VCardText>
          <AppTextField
            v-model="reviewReason"
            placeholder="驳回时填写原因（可选）"
          />
        </VCardText>
      </VCard>
      <FormDrawer
        v-model="reviewOpen"
        :title="reviewDecision === 'approve' ? '批准发布' : '驳回审核'"
        :saving="busy"
        @save="review"
      >
        <VAlert
          type="info"
          variant="tonal"
          class="mb-4"
        >
          {{ reviewTarget?.title }}
        </VAlert>
        <AppTextField
          v-model="reviewReason"
          label="审核意见"
          placeholder="驳回时填写原因；批准时可填写备注"
        />
      </FormDrawer>
    </template>

    <template v-else-if="mode === 'qa'">
      <ListPage
        storage-key="kb-qa"
        title="沉淀问答与经验"
        subtitle="已解决工单可以生成建议问答，批准后才会进入知识库。"
        :items="qa"
        :columns="[{ key: 'question', title: '问题' }, { key: 'answer', title: '答案' }, { key: 'citationLabel', title: '出处' }, { key: 'sourceRef', title: '来源工单' }]"
        @open="openQa"
      />
      <PermissionGate action="suggest">
        <VBtn
          class="mt-4"
          :loading="busy"
          @click="suggest"
        >
          从已解决工单生成建议问答
        </VBtn>
      </PermissionGate>
      <RecordDrawer
        v-if="selectedQa"
        v-model="qaOpen"
        title="问答详情"
      >
        <h6 class="text-h6">
          {{ selectedQa.question }}
        </h6>
        <p class="mt-3">
          {{ selectedQa.answer }}
        </p>
        <VChip
          class="mt-2"
          color="primary"
          variant="tonal"
        >
          {{ selectedQa.citationLabel }}
        </VChip>
        <VBtn
          class="mt-4"
          variant="tonal"
          :to="`/kb/docs/${selectedQa.citationDocId}`"
        >
          打开出处
        </VBtn>
      </RecordDrawer>
    </template>

    <template v-else-if="mode === 'expiring'">
      <ListPage
        storage-key="kb-expiring"
        title="到期提醒"
        subtitle="证书、合同和资质的到期日由代码计算。"
        :items="expiring"
        :columns="[{ key: 'title', title: '文档' }, { key: 'kind', title: '类型' }, { key: 'expiresOn', title: '到期日' }, { key: 'daysRemaining', title: '剩余天数' }, { key: 'owner', title: '负责人' }]"
        date-key="expiresOn"
        @open="row => openDoc(row.docId)"
      >
        <template #item.daysRemaining="{ item }">
          <VChip
            :color="item.status === 'expired' ? 'error' : 'warning'"
            size="small"
            label
          >
            {{ item.status === 'expired' ? '已到期' : '即将到期' }}
          </VChip><span class="ms-2">{{ item.daysRemaining }} 天</span>
        </template>
      </ListPage>
    </template>

    <template v-else-if="mode === 'index'">
      <DetailPage
        title="检索与索引"
        subtitle="重建索引后，检索结果仍引用同一份文档版本。"
      >
        <VCard title="索引状态">
          <VCardText>
            <VAlert
              type="success"
              variant="tonal"
            >
              当前索引版本：v{{ indexVersion }}
            </VAlert><PermissionGate action="update">
              <VBtn
                :loading="busy"
                class="mt-4"
                @click="rebuild"
              >
                重建索引
              </VBtn>
            </PermissionGate>
          </VCardText>
        </VCard><VCard
          class="mt-6"
          title="检索测试"
        >
          <VCardText>
            <div class="d-flex gap-3">
              <AppTextField
                v-model="query"
                label="输入问题或关键词"
                class="flex-grow-1"
                @keyup.enter="searchIndex"
              /><VBtn @click="searchIndex">
                检索
              </VBtn>
            </div>
            <ListPage
              v-if="results.length"
              embedded
              storage-key="kb-index-results"
              title="检索结果"
              :items="results"
              :columns="[{ key: 'title', title: '文档' }, { key: 'version', title: '版本' }, { key: 'paragraph', title: '命中段落' }]"
              @open="row => openDoc(row.docId)"
            >
              <template #item.version="{ item }">
                v{{ item.version }}
              </template>
            </ListPage>
          </VCardText>
        </VCard>
      </DetailPage>
    </template>

    <template v-else-if="mode === 'access'">
      <ListPage
        storage-key="kb-access"
        title="敏感文档访问记录"
        subtitle="包含人和 AI 的查看、下载记录。"
        :items="logs"
        :columns="[{ key: 'title', title: '文档' }, { key: 'actor', title: '访问人' }, { key: 'action', title: '动作' }, { key: 'origin', title: '来源' }, { key: 'at', title: '时间' }]"
        :filters="[{ key: 'origin', label: '来源', items: [{ title: '人工', value: 'human' }, { title: 'AI', value: 'ai' }] }]"
        @open="openAccess"
      />
      <RecordDrawer
        v-if="selectedAccess"
        v-model="accessOpen"
        title="敏感文档访问详情"
      >
        <VList density="compact">
          <VListItem title="文档">
            {{ selectedAccess.title }}
          </VListItem>
          <VListItem title="访问人">
            {{ selectedAccess.actor }}
          </VListItem>
          <VListItem title="动作">
            {{ selectedAccess.action }}
          </VListItem>
          <VListItem title="来源">
            {{ selectedAccess.origin }}
          </VListItem>
          <VListItem title="时间">
            {{ selectedAccess.at }}
          </VListItem>
        </VList>
      </RecordDrawer>
    </template>

    <template v-else-if="mode === 'employee'">
      <DetailPage
        title="员工个人档案"
        :subtitle="`员工：${employeeId}`"
      >
        <VAlert
          type="warning"
          variant="tonal"
          class="mb-6"
        >
          合同、证件和证书属于敏感资料。每次下载都会写入访问审计。
        </VAlert>
        <div class="d-flex flex-wrap gap-3 align-center mb-4">
          <AppSelect
            v-model="employeeFileKind"
            label="档案类型"
            :items="[{ title: '合同', value: 'contract' }, { title: '身份证复印件', value: 'id_copy' }, { title: '证书', value: 'certificate' }]"
            style="max-inline-size: 14rem;"
          />
          <VBtn
            prepend-icon="tabler-upload"
            @click="employeeUploadInput?.click()"
          >
            模拟上传档案
          </VBtn>
          <input
            ref="employeeUploadInput"
            type="file"
            class="d-none"
            @change="uploadEmployee"
          >
        </div>
        <VAlert
          type="info"
          variant="tonal"
          class="mb-4"
        >
          模拟上传只登记文件名、类型、大小、上传人和时间，不保存真实文件；查看/下载会写访问审计。
        </VAlert>
        <ListPage
          embedded
          storage-key="employee-files"
          title="档案文件"
          :items="files"
          :columns="[{ key: 'name', title: '文件' }, { key: 'kind', title: '类型' }, { key: 'size', title: '大小' }, { key: 'expiresOn', title: '有效期' }, { key: 'uploadedAt', title: '上传时间' }]"
          @open="openFile"
        >
          <template #item.name="{ item }">
            <div class="d-flex align-center gap-2">
              <span>{{ item.name }}</span>
              <PermissionGate action="view">
                <VBtn
                  size="small"
                  variant="tonal"
                  @click.stop="download(item)"
                >
                  下载
                </VBtn>
              </PermissionGate>
            </div>
          </template>
        </ListPage>
      </DetailPage>
      <RecordDrawer
        v-if="selectedFile"
        v-model="fileOpen"
        title="档案文件详情"
      >
        <h6 class="text-h6">
          {{ selectedFile.name }}
        </h6>
        <p class="mt-3">
          {{ selectedFile.kind }} · {{ selectedFile.size }}
        </p>
        <p v-if="selectedFile.expiresOn">
          有效期至 {{ selectedFile.expiresOn }}
        </p>
        <PermissionGate action="view">
          <VBtn
            class="mt-4"
            @click="download(selectedFile)"
          >
            下载并记录审计
          </VBtn>
        </PermissionGate>
      </RecordDrawer>
    </template>

    <template v-else-if="mode === 'onboarding'">
      <DetailPage
        title="新人上手"
        subtitle="按当前角色显示任务清单，并提供带出处的只读问答。"
      >
        <VCard title="我的上手清单">
          <VList>
            <VListItem>
              <VProgressLinear
                :model-value="onboardingProgress"
                color="primary"
                height="8"
                rounded
              />
              <div class="text-caption text-medium-emphasis mt-2">
                已完成 {{ onboardingProgress }}%
              </div>
            </VListItem>
            <VListItem
              v-for="item in onboarding"
              :key="item.id"
              :title="item.title"
              :subtitle="item.description"
            >
              <template #prepend>
                <VCheckbox
                  v-model="item.done"
                  hide-details
                  @update:model-value="saveItem(item)"
                />
              </template><template #append>
                <VBtn
                  size="small"
                  variant="tonal"
                  :to="item.route"
                >
                  带我去做
                </VBtn>
              </template>
            </VListItem>
          </VList>
        </VCard><VCard
          v-if="showAi"
          class="mt-6"
          title="上手助手（带出处）"
        >
          <VCardText>
            <div class="d-flex gap-3">
              <AppTextField
                v-model="query"
                label="例如：怎么提交采购单？"
                class="flex-grow-1"
                @keyup.enter="ask"
              /><VBtn
                :loading="busy"
                @click="ask"
              >
                提问
              </VBtn>
            </div><VAlert
              v-if="answer"
              type="info"
              variant="tonal"
              class="mt-4"
            >
              {{ answer.answer }}<VList density="compact">
                <VListItem
                  v-for="citation in answer.citations"
                  :key="citation.docId"
                  :title="citation.label"
                  :to="citation.href"
                  prepend-icon="tabler-link"
                />
              </VList>
            </VAlert>
          </VCardText>
        </VCard>
      </DetailPage>
    </template>

    <template v-else-if="mode === 'onboarding-admin'">
      <div class="d-flex flex-wrap gap-3 align-center mb-4">
        <AppSelect
          v-model="onboardingRole"
          label="角色模板"
          :items="[{ title: '采购', value: 'purchaser' }, { title: '运营', value: 'operator' }, { title: '普通员工', value: 'employee' }, { title: '人事行政', value: 'hr_admin' }]"
          style="max-inline-size: 16rem;"
          @update:model-value="loadOnboardingRole"
        />
        <VBtn
          prepend-icon="tabler-plus"
          @click="addOnboardingItem"
        >
          新增清单步骤
        </VBtn>
      </div>
      <ListPage
        storage-key="onboarding-admin"
        title="上手清单与引导配置"
        subtitle="按角色模板维护清单；修改会写审计。"
        :items="onboarding"
        :columns="[{ key: 'title', title: '任务' }, { key: 'roleId', title: '角色模板' }, { key: 'route', title: '引导页面' }, { key: 'description', title: '说明' }]"
        @open="editOnboarding"
      />
      <PermissionGate action="update">
        <FormDrawer
          v-model="onboardingOpen"
          title="编辑上手清单"
          :saving="busy"
          @save="saveOnboardingDraft"
        >
          <AppTextField
            v-if="onboardingDraft"
            v-model="onboardingDraft.title"
            label="任务"
            class="mb-4"
          />
          <AppTextField
            v-if="onboardingDraft"
            v-model="onboardingDraft.description"
            label="说明"
            class="mb-4"
          />
          <AppTextField
            v-if="onboardingDraft"
            v-model="onboardingDraft.route"
            label="引导页面"
          />
          <AppSelect
            v-if="onboardingDraft"
            v-model="onboardingDraft.roleId"
            label="角色模板"
            :items="[{ title: '采购', value: 'purchaser' }, { title: '运营', value: 'operator' }, { title: '普通员工', value: 'employee' }, { title: '人事行政', value: 'hr_admin' }]"
          />
        </FormDrawer>
      </PermissionGate>
    </template>
  </div>
</template>
