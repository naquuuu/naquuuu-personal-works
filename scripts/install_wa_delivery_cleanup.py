"""Small, guarded source overlay for WhatsApp delivery and presence cleanup."""
import ast

def patch_adapter(source: str) -> str:
    start = source.index('    async def send(self,')
    end = source.index('    async def edit_message(', start)
    block = source[start:end]
    if 'delivery_uncertain' not in block:
        block = block.replace(
            'return SendResult(success=False, error=result.error)',
            'return SendResult(success=False, error="Delivery uncertain; automatic replay stopped",\n'
            '                                      raw_response={"partial_overflow": True, "delivery_uncertain": True})')
        block = block.replace('return SendResult(success=False, error=str(e))',
                              'return SendResult(success=False, error="Delivery uncertain; automatic replay stopped",\n'
                              '                              raw_response={"partial_overflow": True, "delivery_uncertain": True})')
        if block == source[start:end]:
            raise ValueError('Unrecognised WhatsApp send source')
        source = source[:start] + block + source[end:]
    if '    async def stop_typing(self,' not in source:
        marker = '    async def get_chat_info('
        cleanup = '''    async def stop_typing(self, chat_id: str, metadata=None) -> None:
        if await self._bridge_unavailable():
            return
        with suppress(Exception):
            import aiohttp
            async with self._http_session.post(self._bridge_url("typing"),
                    json={"chatId": to_whatsapp_jid(chat_id), "state": "paused"},
                    timeout=aiohttp.ClientTimeout(total=5)):
                pass

'''
        if marker not in source:
            raise ValueError('Missing chat-info anchor')
        source = source.replace(marker, cleanup + marker, 1)
    ast.parse(source)
    return source

def patch_bridge(source: str) -> str:
    if 'const typingLeases = new Map();' in source:
        return source
    marker = "app.post('/typing', async (req, res) => {"
    if marker not in source:
        raise ValueError('Missing typing route')
    source = source.replace(marker, 'const typingLeases = new Map();\n' + marker, 1)
    start = source.index(marker)
    end = source.index('\n});', start) + len('\n});')
    block = source[start:end]
    old = "await sock.sendPresenceUpdate('composing', chatId);"
    if old not in block:
        raise ValueError('Unrecognised typing implementation')
    new = '''const state = req.body.state || 'composing';
    if (!['composing', 'paused'].includes(state)) return res.status(400).json({ error: 'Invalid presence state' });
    const previous = typingLeases.get(chatId);
    if (previous) clearTimeout(previous);
    typingLeases.delete(chatId);
    await sock.sendPresenceUpdate(state, chatId);
    if (state === 'composing') {
      // Safety lease expires even if the gateway crashes before stop_typing.
      if (typingLeases.size >= 128) {
        const [oldChat, timer] = typingLeases.entries().next().value;
        clearTimeout(timer); typingLeases.delete(oldChat);
        if (sock && connectionState === 'connected') sock.sendPresenceUpdate('paused', oldChat).catch(() => {});
      }
      const timer = setTimeout(() => {
        typingLeases.delete(chatId);
        if (sock && connectionState === 'connected') sock.sendPresenceUpdate('paused', chatId).catch(() => {});
      }, 15000);
      timer.unref();
      typingLeases.set(chatId, timer);
    }'''
    block = block.replace(old, new, 1)
    return source[:start] + block + source[end:]
