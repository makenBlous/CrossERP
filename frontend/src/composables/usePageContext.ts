const selectedRecordId = ref<string | null>(null)

export function usePageContext() {
  function setSelected(id: string | null) {
    selectedRecordId.value = id
  }

  return { selectedRecordId, setSelected }
}
