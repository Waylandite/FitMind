import { useCallback, useEffect, useRef } from 'react'

function isNearBottom(element, threshold) {
  const distance = element.scrollHeight - element.scrollTop - element.clientHeight
  return distance <= threshold
}

function useSmartAutoScroll({ threshold = 88 } = {}) {
  const viewportRef = useRef(null)
  const bottomAnchorRef = useRef(null)
  const shouldTrackRef = useRef(true)
  const programmaticScrollRef = useRef(false)
  const resetProgrammaticTimerRef = useRef(null)

  const markProgrammaticScroll = useCallback(() => {
    programmaticScrollRef.current = true

    if (resetProgrammaticTimerRef.current) {
      window.clearTimeout(resetProgrammaticTimerRef.current)
    }

    resetProgrammaticTimerRef.current = window.setTimeout(() => {
      programmaticScrollRef.current = false
      resetProgrammaticTimerRef.current = null
    }, 180)
  }, [])

  const scrollToBottom = useCallback(
    (behavior = 'smooth') => {
      const viewport = viewportRef.current
      if (!viewport) {
        return
      }

      markProgrammaticScroll()
      window.requestAnimationFrame(() => {
        viewport.scrollTo({
          top: viewport.scrollHeight,
          behavior,
        })
      })
    },
    [markProgrammaticScroll],
  )

  const requestAutoScroll = useCallback(
    (behavior = 'smooth') => {
      const viewport = viewportRef.current
      if (!viewport) {
        return
      }

      if (!shouldTrackRef.current && !isNearBottom(viewport, threshold)) {
        return
      }

      shouldTrackRef.current = true
      scrollToBottom(behavior)
    },
    [scrollToBottom, threshold],
  )

  const resumeAutoScroll = useCallback(
    (behavior = 'auto') => {
      shouldTrackRef.current = true
      scrollToBottom(behavior)
    },
    [scrollToBottom],
  )

  const stopAutoScroll = useCallback(() => {
    shouldTrackRef.current = false
  }, [])

  const handleScroll = useCallback(() => {
    const viewport = viewportRef.current
    if (!viewport || programmaticScrollRef.current) {
      return
    }

    shouldTrackRef.current = isNearBottom(viewport, threshold)
  }, [threshold])

  const handleWheel = useCallback(
    (event) => {
      const viewport = viewportRef.current
      if (!viewport) {
        return
      }

      if (event.deltaY < 0 && !isNearBottom(viewport, threshold)) {
        stopAutoScroll()
      }
    },
    [stopAutoScroll, threshold],
  )

  const handleTouchMove = useCallback(() => {
    const viewport = viewportRef.current
    if (viewport && !isNearBottom(viewport, threshold)) {
      stopAutoScroll()
    }
  }, [stopAutoScroll, threshold])

  useEffect(
    () => () => {
      if (resetProgrammaticTimerRef.current) {
        window.clearTimeout(resetProgrammaticTimerRef.current)
      }
    },
    [],
  )

  return {
    viewportRef,
    bottomAnchorRef,
    requestAutoScroll,
    resumeAutoScroll,
    handleScroll,
    handleWheel,
    handleTouchMove,
  }
}

export default useSmartAutoScroll
