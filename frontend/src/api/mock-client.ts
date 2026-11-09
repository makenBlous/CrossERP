/**
 * 静态原型的数据出口。
 * 以后把各领域函数里的 readMock 换成请求 /api/v1，页面不用改。
 */
export function readMock<T>(data: T): Promise<T> {
  return Promise.resolve(structuredClone(data))
}
