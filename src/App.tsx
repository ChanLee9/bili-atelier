import { useDeferredValue, useEffect, useState } from 'react'
import './App.css'

type QualityOption = {
  id: string
  label: string
  badge: string
  description: string
}

type Episode = {
  id: string
  index: number
  title: string
  duration_text: string
  source_url: string
  thumbnail?: string | null
}

type CollectionSummary = {
  title: string
  source_url: string
  uploader?: string | null
  thumbnail?: string | null
  episode_count: number
  episodes: Episode[]
  quality_options: QualityOption[]
}

type DownloadItem = {
  episode_id: string
  title: string
  status: 'pending' | 'running' | 'completed' | 'failed'
  output_path?: string | null
  detail?: string | null
}

type DownloadJob = {
  job_id: string
  status: 'queued' | 'running' | 'completed' | 'failed'
  source_url: string
  collection_title: string
  quality_id: string
  download_directory: string
  total_episodes: number
  completed_episodes: number
  failed_episodes: number
  progress_ratio: number
  items: DownloadItem[]
  error?: string | null
}

const defaultUrl =
  'https://www.bilibili.com/video/BV1fsHcz6E2C/?spm_id_from=333.1387.favlist.content.click&vd_source=bc5b3bfae3c52a7534b6639a09f91685'

const jobStatusText: Record<DownloadJob['status'], string> = {
  queued: '准备中',
  running: '下载中',
  completed: '已完成',
  failed: '失败',
}

const itemStatusText: Record<DownloadItem['status'], string> = {
  pending: '排队中',
  running: '下载中',
  completed: '已完成',
  failed: '失败',
}

async function parseResponse(response: Response) {
  const text = await response.text()
  if (!text) {
    return null
  }

  try {
    return JSON.parse(text)
  } catch {
    return { detail: text }
  }
}

function getJobHeadline(job: DownloadJob | null) {
  if (!job) {
    return '暂无下载任务'
  }
  if (job.failed_episodes > 0 && job.completed_episodes > 0 && job.status === 'completed') {
    return '部分完成'
  }
  return jobStatusText[job.status]
}

function getFocusedDownloadItem(job: DownloadJob | null) {
  if (!job) {
    return null
  }

  const running = job.items.find((item) => item.status === 'running')
  if (running) {
    return { label: '当前下载', item: running }
  }

  const pending = job.items.find((item) => item.status === 'pending')
  if (pending) {
    return { label: '即将开始', item: pending }
  }

  const recent = [...job.items]
    .reverse()
    .find((item) => item.status === 'completed' || item.status === 'failed')

  if (recent) {
    return { label: '最近状态', item: recent }
  }

  return null
}

function App() {
  const [url, setUrl] = useState(defaultUrl)
  const [collection, setCollection] = useState<CollectionSummary | null>(null)
  const [selectedQuality, setSelectedQuality] = useState('720p')
  const [selectedEpisodeIds, setSelectedEpisodeIds] = useState<string[]>([])
  const [inspectError, setInspectError] = useState<string | null>(null)
  const [downloadError, setDownloadError] = useState<string | null>(null)
  const [isInspecting, setIsInspecting] = useState(false)
  const [isStartingDownload, setIsStartingDownload] = useState(false)
  const [downloadJob, setDownloadJob] = useState<DownloadJob | null>(null)
  const [episodeQuery, setEpisodeQuery] = useState('')
  const deferredQuery = useDeferredValue(episodeQuery.trim().toLowerCase())

  const visibleEpisodes = collection
    ? collection.episodes.filter((episode) => {
        if (!deferredQuery) {
          return true
        }
        return episode.title.toLowerCase().includes(deferredQuery)
      })
    : []

  const selectedCount = selectedEpisodeIds.length
  const allSelected =
    collection !== null && collection.episodes.length > 0 && selectedCount === collection.episodes.length
  const focusedDownloadItem = getFocusedDownloadItem(downloadJob)

  async function inspectCollection() {
    const trimmedUrl = url.trim()
    if (!trimmedUrl) {
      setInspectError('请先输入一个 B 站合集或多 P 视频链接。')
      return
    }

    setIsInspecting(true)
    setInspectError(null)
    setDownloadError(null)
    setDownloadJob(null)
    setCollection(null)
    setSelectedEpisodeIds([])
    setEpisodeQuery('')

    try {
      const response = await fetch('/api/collections/inspect', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ url: trimmedUrl }),
      })
      const payload = (await parseResponse(response)) as CollectionSummary | { detail?: string } | null
      if (!response.ok) {
        throw new Error(payload && 'detail' in payload ? payload.detail ?? '解析链接失败。' : '解析链接失败。')
      }

      const parsedCollection = payload as CollectionSummary
      setCollection(parsedCollection)
      setSelectedQuality(parsedCollection.quality_options[2]?.id ?? parsedCollection.quality_options[0]?.id ?? '720p')
      setSelectedEpisodeIds(parsedCollection.episodes.map((episode) => episode.id))
    } catch (error) {
      setInspectError(error instanceof Error ? error.message : '解析链接失败，请稍后重试。')
    } finally {
      setIsInspecting(false)
    }
  }

  async function startDownload() {
    if (!collection) {
      setDownloadError('请先解析链接，再开始下载。')
      return
    }

    const episodeIdsSnapshot = [...selectedEpisodeIds]
    if (episodeIdsSnapshot.length === 0) {
      setDownloadError('请至少勾选一个分集后再开始下载。')
      return
    }

    setIsStartingDownload(true)
    setDownloadError(null)

    try {
      const response = await fetch('/api/downloads', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          source_url: collection.source_url,
          quality_id: selectedQuality,
          episode_ids: episodeIdsSnapshot,
        }),
      })
      const payload = (await parseResponse(response)) as DownloadJob | { detail?: string } | null
      if (!response.ok) {
        throw new Error(payload && 'detail' in payload ? payload.detail ?? '创建下载任务失败。' : '创建下载任务失败。')
      }
      setDownloadJob(payload as DownloadJob)
    } catch (error) {
      setDownloadError(error instanceof Error ? error.message : '创建下载任务失败，请稍后重试。')
    } finally {
      setIsStartingDownload(false)
    }
  }

  function toggleEpisode(id: string) {
    setSelectedEpisodeIds((current) =>
      current.includes(id) ? current.filter((value) => value !== id) : [...current, id],
    )
  }

  function selectAllEpisodes() {
    if (!collection) {
      return
    }
    setSelectedEpisodeIds(collection.episodes.map((episode) => episode.id))
  }

  function clearEpisodeSelection() {
    setSelectedEpisodeIds([])
  }

  useEffect(() => {
    if (!downloadJob) {
      return
    }
    if (downloadJob.status === 'completed' || downloadJob.status === 'failed') {
      return
    }

    const timer = window.setInterval(async () => {
      const response = await fetch(`/api/downloads/${downloadJob.job_id}`)
      const payload = (await parseResponse(response)) as DownloadJob | null
      if (response.ok && payload) {
        setDownloadJob(payload)
      }
    }, 1500)

    return () => window.clearInterval(timer)
  }, [downloadJob])

  return (
    <main className="page-shell">
      <div className="backdrop backdrop-left" />
      <div className="backdrop backdrop-right" />

      <section className="hero-panel">
        <div className="hero-copy">
          <p className="eyebrow">Bili Atelier</p>
          <h1>把 B 站合集当成作品集一样整理，再优雅地保存到本地。</h1>
          <p className="hero-text">
            输入一个合集或多 P 视频链接，预览所有分集，选择清晰度与下载范围，再用更清晰的状态反馈追踪整个下载过程。
          </p>
        </div>
        <div className="hero-rail">
          <div className="hero-metrics">
            <article className="metric-card">
              <span>解析结果</span>
              <strong>{collection?.episode_count ?? 0}</strong>
              <p>当前链接识别出的分集数量</p>
            </article>
            <article className="metric-card">
              <span>已选分集</span>
              <strong>{selectedCount}</strong>
              <p>当前准备下载的分集数量</p>
            </article>
            <article className="metric-card">
              <span>下载进度</span>
              <strong>{downloadJob ? `${Math.round(downloadJob.progress_ratio * 100)}%` : '待开始'}</strong>
              <p>当前下载任务的总体完成度</p>
            </article>
          </div>

          <aside className="hero-sidecard">
            <div className="hero-sidecard-header">
              <p className="section-kicker">首屏速览</p>
              <h2>把这块空间用来告诉你现在能做什么</h2>
            </div>

            <div className="hero-sidecard-grid">
              <article className="sidecard-item">
                <span>支持内容</span>
                <strong>公开合集 / 多 P 视频</strong>
                <p>适合按合集整理课程、访谈、教程和系列视频。</p>
              </article>
              <article className="sidecard-item">
                <span>下载方式</span>
                <strong>多线程并发</strong>
                <p>会自动启用并发 worker 与分片下载，更充分利用本机 CPU 资源。</p>
              </article>
            </div>

            <div className="hero-sidecard-flow">
              <span className="flow-step">1. 粘贴链接并解析</span>
              <span className="flow-step">2. 勾选分集与清晰度</span>
              <span className="flow-step">3. 创建任务并跟踪状态</span>
            </div>

            <div className="hero-sidecard-note">
              <strong>{collection ? '当前已准备好进入下载阶段' : '等待你输入第一个链接'}</strong>
              <p>
                {collection
                  ? `已识别 ${collection.episode_count} 个分集，现在可以继续筛选并开始下载。`
                  : '首屏现在不仅展示统计数字，也会提示当前支持能力和推荐操作路径。'}
              </p>
            </div>
          </aside>
        </div>
      </section>

      <section className="workspace-grid">
        <section className="panel intake-panel">
          <div className="panel-heading">
            <div>
              <p className="section-kicker">链接解析</p>
              <h2>输入一个 B 站合集链接</h2>
            </div>
            <span className="status-pill">仅支持公开或你有权限访问的内容</span>
          </div>

          <label className="field-label" htmlFor="collection-url">
            合集或多 P 视频链接
          </label>
          <div className="url-row">
            <input
              id="collection-url"
              className="url-input"
              value={url}
              onChange={(event) => setUrl(event.target.value)}
              placeholder="https://www.bilibili.com/video/..."
              disabled={isInspecting}
            />
            <button className="primary-button" onClick={inspectCollection} disabled={isInspecting}>
              {isInspecting ? '解析中...' : '开始解析'}
            </button>
          </div>

          <div className="support-copy">
            后端会校验链接、读取合集信息、识别分集列表，并为前端提供可选清晰度与下载任务状态。
          </div>

          {isInspecting ? (
            <div className="inline-progress">
              <div className="spinner" />
              <div className="inline-progress-copy">
                <strong>正在解析链接</strong>
                <p>正在读取合集标题、分集列表和封面信息，请稍候。</p>
              </div>
              <div className="loading-bar">
                <div className="loading-bar-indeterminate" />
              </div>
            </div>
          ) : null}

          {inspectError ? <p className="message error">{inspectError}</p> : null}

          {collection ? (
            <div className="collection-card">
              <div className="collection-art">
                {collection.thumbnail ? (
                  <img src={collection.thumbnail} alt={collection.title} />
                ) : (
                  <div className="art-placeholder">BA</div>
                )}
              </div>
              <div className="collection-copy">
                <p className="section-kicker">合集信息</p>
                <h3>{collection.title}</h3>
                <p>{collection.uploader ?? '未知 UP 主'}</p>
                <p>共 {collection.episode_count} 个分集，已默认全选。</p>
              </div>
            </div>
          ) : (
            !isInspecting && (
              <div className="collection-placeholder">
                <p>解析完成后，这里会展示封面、标题、UP 主和分集数量。</p>
              </div>
            )
          )}

          <div className="panel-heading compact">
            <div>
              <p className="section-kicker">清晰度</p>
              <h2>选择下载质量</h2>
            </div>
          </div>

          <div className="quality-grid">
            {(collection?.quality_options ?? []).map((quality) => (
              <button
                key={quality.id}
                className={`quality-card ${selectedQuality === quality.id ? 'selected' : ''}`}
                onClick={() => setSelectedQuality(quality.id)}
                disabled={!collection || isInspecting}
              >
                <span className="quality-badge">{quality.badge}</span>
                <strong>{quality.label}</strong>
                <p>{quality.description}</p>
              </button>
            ))}
          </div>

          <div className="download-actions">
            <button className="ghost-button" onClick={selectAllEpisodes} disabled={!collection || allSelected}>
              全选
            </button>
            <button className="ghost-button" onClick={clearEpisodeSelection} disabled={selectedCount === 0}>
              清空
            </button>
            <button
              className="primary-button"
              onClick={startDownload}
              disabled={isStartingDownload || !collection || isInspecting || selectedCount === 0}
            >
              {isStartingDownload ? '创建任务中...' : '开始下载'}
            </button>
          </div>

          <div className="selection-hint">
            {collection
              ? `当前已选择 ${selectedCount} / ${collection.episode_count} 个分集`
              : '请先解析链接后再选择分集'}
          </div>

          {downloadError ? <p className="message error">{downloadError}</p> : null}
        </section>

        <section className="panel episodes-panel">
          <div className="panel-heading">
            <div>
              <p className="section-kicker">分集选择</p>
              <h2>在可滚动列表中勾选需要的内容</h2>
            </div>
            <input
              className="search-input"
              value={episodeQuery}
              onChange={(event) => setEpisodeQuery(event.target.value)}
              placeholder="搜索分集标题..."
              disabled={!collection}
            />
          </div>

          {collection ? (
            <div className="episodes-toolbar">
              <p>
                可见 {visibleEpisodes.length} 个分集，已勾选 {selectedCount} 个
              </p>
              <div className="episodes-toolbar-actions">
                <button className="ghost-button compact-button" onClick={selectAllEpisodes} disabled={allSelected}>
                  全部勾选
                </button>
                <button className="ghost-button compact-button" onClick={clearEpisodeSelection} disabled={selectedCount === 0}>
                  取消全选
                </button>
              </div>
            </div>
          ) : null}

          <div className="episodes-scroll">
            {isInspecting ? (
              <div className="empty-state">
                <p>正在解析链接，分集列表准备好后会显示在这里。</p>
              </div>
            ) : visibleEpisodes.length === 0 ? (
              <div className="empty-state">
                <p>{collection ? '没有匹配到分集，请换个关键词试试。' : '解析一个合集后，这里会出现可滚动的分集列表。'}</p>
              </div>
            ) : (
              <div className="episodes-list">
                {visibleEpisodes.map((episode) => {
                  const checked = selectedEpisodeIds.includes(episode.id)
                  return (
                    <label key={episode.id} className={`episode-card ${checked ? 'checked' : ''}`}>
                      <input type="checkbox" checked={checked} onChange={() => toggleEpisode(episode.id)} />
                      <div className="episode-cover">
                        {episode.thumbnail ? (
                          <img src={episode.thumbnail} alt={episode.title} />
                        ) : (
                          <span>{episode.index.toString().padStart(2, '0')}</span>
                        )}
                      </div>
                      <div className="episode-meta">
                        <span className="episode-index">第 {episode.index} 集</span>
                        <strong>{episode.title}</strong>
                        <p>{episode.duration_text}</p>
                      </div>
                    </label>
                  )
                })}
              </div>
            )}
          </div>
        </section>
      </section>

      <section className="panel progress-panel">
        <div className="panel-heading">
          <div>
            <p className="section-kicker">下载状态</p>
            <h2>实时查看当前任务进展</h2>
          </div>
          <span className="status-pill">{getJobHeadline(downloadJob)}</span>
        </div>

        {isStartingDownload && !downloadJob ? (
          <div className="inline-progress inline-progress-large">
            <div className="spinner" />
            <div className="inline-progress-copy">
              <strong>正在创建下载任务</strong>
              <p>后端正在整理选中的分集并分配下载 worker，请稍候。</p>
            </div>
            <div className="loading-bar">
              <div className="loading-bar-indeterminate" />
            </div>
          </div>
        ) : downloadJob ? (
          <>
            <div className="progress-bar">
              <div className="progress-value" style={{ width: `${downloadJob.progress_ratio * 100}%` }} />
            </div>

            <div className="job-summary">
              <p>
                下载目录：<code>{downloadJob.download_directory}</code>
              </p>
              <p>
                已完成 {downloadJob.completed_episodes} / {downloadJob.total_episodes}，失败 {downloadJob.failed_episodes}
              </p>
            </div>

            {focusedDownloadItem ? (
              <div className="download-focus-card">
                <span>{focusedDownloadItem.label}</span>
                <strong>{focusedDownloadItem.item.title}</strong>
                <p>{focusedDownloadItem.item.detail ?? itemStatusText[focusedDownloadItem.item.status]}</p>
              </div>
            ) : null}

            <div className="job-items">
              {downloadJob.items.map((item) => (
                <article key={item.episode_id} className={`job-item status-${item.status}`}>
                  <div>
                    <strong>{item.title}</strong>
                    <p>{item.detail ?? itemStatusText[item.status]}</p>
                  </div>
                  <div className="job-tail">
                    <span>{itemStatusText[item.status]}</span>
                    {item.output_path ? <code>{item.output_path}</code> : null}
                  </div>
                </article>
              ))}
            </div>

            {downloadJob.error ? <p className="message error">{downloadJob.error}</p> : null}
          </>
        ) : (
          <div className="empty-state">
            <p>解析链接、选择分集和清晰度后，下载任务会显示在这里。</p>
          </div>
        )}
      </section>
    </main>
  )
}

export default App
