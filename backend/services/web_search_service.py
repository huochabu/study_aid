from duckduckgo_search import DDGS
import logging

logger = logging.getLogger(__name__)

class WebSearchService:
    def __init__(self):
        # Specific proxy setup for China environment
        # Try common local proxy ports: 7890 (Clash), 10809 (v2ray)
        self.proxies = None
        import requests
        
        candidates = [
            "http://127.0.0.1:7890",
            "http://127.0.0.1:10809",
            "http://127.0.0.1:1080"
        ]
        
        for p in candidates:
            try:
                # Quick test
                requests.get("https://www.google.com", proxies={"http": p, "https": p}, timeout=2)
                self.proxies = p
                logger.info(f"✅ [WebSearch] Found working proxy: {p}")
                break
            except:
                pass
                
        if self.proxies:
            self.ddgs = DDGS(proxy=self.proxies, timeout=20)
        else:
            logger.warning("⚠️ [WebSearch] No working proxy found. Search might fail in CN.")
            self.ddgs = DDGS(timeout=20)

    def search_for_context(self, keywords: list, max_results: int = 3) -> str:
        """
        根据关键词搜索网络信息，返回格式化的字符串
        """
        if not keywords:
            return ""
        
        # 构造查询语句：选取前3个关键词
        query = " ".join(keywords[:3])
        logger.info(f"🔍 [WebSearch] Searching for: {query}")
        
        try:
            results = self.ddgs.text(query, max_results=max_results)
            if not results:
                return ""
            
            context_text = "\n\n【🌐 网络实时增强信息】\n"
            for i, res in enumerate(results):
                title = res.get('title', 'No Title')
                body = res.get('body', 'No Content')
                href = res.get('href', '#')
                context_text += f"{i+1}. **{title}**: {body} ([Source]({href}))\n"
            
            return context_text
        except Exception as e:
            logger.error(f"❌ [WebSearch] Search failed: {str(e)}")
            return ""

# 单例实例
web_search_service = WebSearchService()
