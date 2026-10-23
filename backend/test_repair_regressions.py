"""Offline regressions for provider, session, speech and permission repairs."""
import asyncio
from types import SimpleNamespace as NS
from unittest.mock import AsyncMock, MagicMock
import httpx
import pytest
from backend import router, memory
from backend.config import settings
from backend.session import Session

class FakeStream:
    def __init__(self, chunks):
        self.chunks = chunks
    async def __aenter__(self):
        return self
    async def __aexit__(self, *args):
        pass
    def __aiter__(self):
        return self.iterate()
    async def iterate(self):
        for chunk in self.chunks:
            yield chunk

@pytest.fixture(autouse=True)
def isolation(tmp_path, monkeypatch):
    monkeypatch.setattr(memory, 'DB_PATH', tmp_path / 'memory.db')
    monkeypatch.setattr(settings, 'MODEL_FALLBACK_ENABLED', True)
    monkeypatch.setattr(router, '_recovered_models', {})

@pytest.mark.asyncio
@pytest.mark.parametrize('provider,module,method', [('Groq','groq','AsyncGroq'), ('NVIDIA','openai','AsyncOpenAI')])
async def test_cloud_request_and_cleanup(provider, module, method, monkeypatch):
    import importlib
    client = NS(chat=NS(completions=NS(create=AsyncMock(return_value=FakeStream([NS(choices=[NS(delta=NS(content='ans'))]), NS(choices=[NS(delta=NS(content='wer'))])])))), close=AsyncMock())
    factory = MagicMock(return_value=client)
    monkeypatch.setattr(importlib.import_module(module), method, factory)
    monkeypatch.setattr(settings, provider.upper()+'_API_KEY', 'unit-test-only')
    result = await router.route_inference('next', provider, conversation=[{'role':'user','content':'previous'},{'role':'assistant','content':'reply'}])
    assert result['text'] == 'answer'
    assert client.chat.completions.create.call_args.kwargs['messages'][1:3] == [{'role':'user','content':'previous'},{'role':'assistant','content':'reply'}]
    client.close.assert_awaited_once()

@pytest.mark.asyncio
async def test_gemini_roles_and_cleanup(monkeypatch):
    from google import genai
    create = AsyncMock(return_value=FakeStream([NS(text='ans'),NS(text='wer')]))
    client = NS(aio=NS(models=NS(generate_content_stream=create), aclose=AsyncMock()), close=MagicMock())
    monkeypatch.setattr(genai, 'Client', MagicMock(return_value=client))
    monkeypatch.setattr(settings, 'GEMINI_API_KEY', 'unit-test-only')
    result = await router.route_inference('next', 'Gemini', conversation=[{'role':'assistant','content':'past'}])
    assert result['text'] == 'answer'
    assert create.call_args.kwargs['contents'][0].role == 'model'
    client.aio.aclose.assert_awaited_once()
    client.close.assert_called_once()

@pytest.mark.asyncio
async def test_ollama_chat_payload(monkeypatch):
    client_type = httpx.AsyncClient
    seen = []
    def handle(request):
        import json
        seen.append(json.loads(request.content))
        return httpx.Response(200, content=b'{"message":{"content":"local"},"done":true}\n')
    monkeypatch.setattr(router.httpx, 'AsyncClient', lambda **kw: client_type(transport=httpx.MockTransport(handle)))
    result = await router.route_inference('next', 'Ollama')
    assert result['text'] == 'local'
    assert seen[0]['stream'] is True

@pytest.mark.asyncio
async def test_fallback_switching_and_no_history_leak(monkeypatch):
    seen = []
    async def groq(prompt, system):
        seen.append(router._messages(prompt, system))
        await asyncio.sleep(0)
        return None
    async def gemini(prompt, system):
        return router._messages(prompt, system)[-2]['content']
    monkeypatch.setattr(router, 'generate_groq', groq)
    monkeypatch.setattr(router, 'generate_gemini', gemini)
    a,b = await asyncio.gather(*(router.route_inference('next','Groq', conversation=[{'role':'user','content':name}]) for name in ('A','B')))
    assert (a['text'],b['text']) == ('A','B')
    assert a['fallback_used'] and b['fallback_used']
    assert router._history.get() == ()

@pytest.mark.asyncio
async def test_disabled_fallback_and_cancel(monkeypatch):
    monkeypatch.setattr(settings, 'MODEL_FALLBACK_ENABLED', False)
    monkeypatch.setattr(router, 'generate_groq', AsyncMock(return_value=None))
    cloud = AsyncMock(return_value='not allowed')
    monkeypatch.setattr(router,'generate_gemini',cloud)
    result = await router.route_inference('test','Groq')
    assert result['unavailable']
    cloud.assert_not_awaited()
    monkeypatch.setattr(router,'generate_groq',AsyncMock(side_effect=asyncio.CancelledError))
    with pytest.raises(asyncio.CancelledError):
        await router.route_inference('test','Groq')
    cloud.assert_not_awaited()

@pytest.mark.asyncio
@pytest.mark.parametrize('kind', [[], {}, None, 123])
async def test_bad_event_does_not_break_session(kind):
    ws = NS(send_json=AsyncMock())
    session = Session(ws,asyncio.Lock())
    await session.dispatch({'type':kind})
    assert ws.send_json.call_args.args[0]['type'] == 'ERROR'
    await session.dispatch({'type':'PING'})
    assert ws.send_json.call_args.args[0]['type'] == 'PONG'

@pytest.mark.asyncio
async def test_speech_file_is_played_and_removed(tmp_path,monkeypatch):
    import backend.session as sessions
    path = tmp_path/'speech.mp3'
    path.write_bytes(b'test')
    monkeypatch.setattr(sessions.tts_manager,'synthesize',AsyncMock(return_value={'success':True,'file_path':str(path)}))
    play = AsyncMock(return_value=True)
    monkeypatch.setattr(sessions.tts_manager,'play_audio_async',play)
    monkeypatch.setattr(sessions.tts_manager,'stop_playback',MagicMock())
    ws = NS(send_json=AsyncMock())
    await Session(ws,asyncio.Lock()).finish({'status':'SUCCESS','response':'hello'},speak=True)
    play.assert_awaited_once()
    assert not path.exists()
    assert ws.send_json.call_args.args[0]['payload']['status'] == 'IDLE'

@pytest.mark.asyncio
async def test_repeated_cancel_keeps_atomic_lock(monkeypatch):
    import backend.session as sessions
    started,release = asyncio.Event(),asyncio.Event()
    async def command(*args,**kwargs):
        await session.atomic(action())
        return {'status':'SUCCESS'}
    async def action():
        started.set()
        await release.wait()
    session = Session(NS(send_json=AsyncMock()),asyncio.Lock())
    monkeypatch.setattr(sessions,'orchestrate_task',command)
    monkeypatch.setattr(sessions.tts_manager,'stop_playback',MagicMock())
    await session.dispatch({'type':'USER_INPUT','payload':{'text':'test'}})
    await started.wait()
    await session.dispatch({'type':'INTERRUPT'})
    await asyncio.sleep(0)
    await session.dispatch({'type':'INTERRUPT'})
    assert session.desktop_lock.locked()
    release.set()
    await session.worker
    assert not session.desktop_lock.locked()


def test_app_verification_does_not_kill(monkeypatch):
    from backend.tools import app_control
    monkeypatch.setattr(app_control,'is_app_running',lambda _: {'is_running':True})
    monkeypatch.setattr(app_control.time,'sleep',lambda _:None)
    processes = MagicMock()
    monkeypatch.setattr(app_control.psutil,'process_iter',processes)
    assert app_control.verify_app_closed({}, {'name':'notepad'})[0] is False
    processes.assert_not_called()

@pytest.mark.asyncio
async def test_launch_arguments_require_confirmation(monkeypatch):
    from backend.tools.registry import tool_registry
    launch = tool_registry.get('app.launch')
    execute = MagicMock()
    monkeypatch.setattr(launch,'execute_fn',execute)
    result = await tool_registry.execute('app.launch', {'name':'terminal','args':['powershell','-Command','anything']})
    assert not result.success
    execute.assert_not_called()


def test_validation_rejects_unknown_and_nonfinite():
    from backend.tools.registry import tool_registry
    tool = tool_registry.get('system.set_volume')
    for args in ({'level':50,'extra':1}, {'level':True}, {'level':float('nan')}):
        assert not tool_registry.validate_arguments(tool,args)[0]

@pytest.mark.parametrize('operation', ['copy_file','move_file'])
def test_files_never_overwrite_existing_destination(operation,tmp_path):
    from backend.tools import file_control
    source,destination = tmp_path/'a.txt',tmp_path/'b.txt'
    source.write_text('source')
    destination.write_text('keep')
    result = getattr(file_control,operation)(str(source),str(destination))
    assert not result['success']
    assert source.read_text() == 'source'
    assert destination.read_text() == 'keep'


def test_invalid_plan_does_not_execute_valid_subset():
    import json
    from backend.tools.planner import parse_llm_tool_calls
    plan = {'steps':[{'tool':'app.launch','arguments':{'name':'notepad'}},{'tool':'invented.tool','arguments':{}}]}
    assert parse_llm_tool_calls(json.dumps(plan)) is None


def test_http_websocket_startup_and_shutdown():
    from backend.main import app
    from fastapi.testclient import TestClient
    with TestClient(app) as client:
        assert client.get('/health').json()['status'] == 'online'
        with client.websocket_connect('/ws/nova') as ws:
            for expected in ('STATE_CHANGE','MEMORY_SYNC','SKILLS_SYNC','MODEL_CONFIG'):
                assert ws.receive_json()['type'] == expected
            ws.send_json({'type':[]})
            assert ws.receive_json()['type'] == 'ERROR'
            ws.send_bytes(b'invalid binary')
            assert ws.receive_json()['type'] == 'ERROR'
            ws.send_json({'type':'PING'})
            assert ws.receive_json()['type'] == 'PONG'
    assert not app.state.connections

@pytest.mark.asyncio
async def test_provider_error_does_not_reveal_key(monkeypatch):
    import groq
    client = NS(chat=NS(completions=NS(create=AsyncMock(side_effect=RuntimeError('secret-api-key')))),close=AsyncMock())
    monkeypatch.setattr(groq,'AsyncGroq',MagicMock(return_value=client))
    monkeypatch.setattr(settings,'GROQ_API_KEY','secret-api-key')
    monkeypatch.setattr(settings,'MODEL_FALLBACK_ENABLED',False)
    result = await router.route_inference('test','Groq')
    assert result['unavailable']
    assert 'RuntimeError' in result['text']
    assert 'secret-api-key' not in str(result)
    client.close.assert_awaited_once()

@pytest.mark.asyncio
@pytest.mark.parametrize('provider', ['Gemini','Groq','NVIDIA','Ollama'])
async def test_model_discovery(provider,monkeypatch):
    client_type = httpx.AsyncClient
    def handle(request):
        body = {'models':[{'name':'test-model'}]} if provider in ('Gemini','Ollama') else {'data':[{'id':'test-model'}]}
        return httpx.Response(200,json=body)
    if provider != 'Ollama':
        monkeypatch.setattr(settings,provider.upper()+'_API_KEY','unit-test')
    monkeypatch.setattr(router.httpx,'AsyncClient',lambda **kw:client_type(transport=httpx.MockTransport(handle)))
    result = await router.discover_models(provider)
    assert result['available'] and result['models'] == ['test-model']

@pytest.mark.asyncio
async def test_broken_stream_never_returns_partial_success(monkeypatch):
    import groq
    class BrokenStream(FakeStream):
        async def iterate(self):
            yield NS(choices=[NS(delta=NS(content='partial'))])
            raise RuntimeError('connection lost')
    client = NS(chat=NS(completions=NS(create=AsyncMock(return_value=BrokenStream([])))),close=AsyncMock())
    monkeypatch.setattr(groq,'AsyncGroq',MagicMock(return_value=client))
    monkeypatch.setattr(settings,'GROQ_API_KEY','unit-test')
    monkeypatch.setattr(router,'generate_gemini',AsyncMock(return_value='complete fallback'))
    result = await router.route_inference('hello','Groq')
    assert result['text'] == 'complete fallback'
    assert result['fallback_used']
    client.close.assert_awaited_once()

@pytest.mark.asyncio
async def test_rate_limit_is_reported_without_raw_response(monkeypatch):
    import groq
    request = httpx.Request('POST','https://example.invalid')
    response = httpx.Response(429,request=request)
    failure = httpx.HTTPStatusError('private response body',request=request,response=response)
    client = NS(chat=NS(completions=NS(create=AsyncMock(side_effect=failure))),close=AsyncMock())
    monkeypatch.setattr(groq,'AsyncGroq',MagicMock(return_value=client))
    monkeypatch.setattr(settings,'GROQ_API_KEY','unit-test')
    monkeypatch.setattr(settings,'MODEL_FALLBACK_ENABLED',False)
    result = await router.route_inference('hello','Groq')
    assert 'HTTP 429' in result['text']
    assert 'private response body' not in str(result)


@pytest.mark.asyncio
@pytest.mark.parametrize('code', [404, 410])
async def test_retired_model_recovers_once_and_caches_success(code, monkeypatch):
    import groq
    request = httpx.Request('POST', 'https://example.invalid')
    failure = httpx.HTTPStatusError('retired', request=request, response=httpx.Response(code, request=request))
    create = AsyncMock(side_effect=[failure, FakeStream([NS(choices=[NS(delta=NS(content='OK'))])]), FakeStream([NS(choices=[NS(delta=NS(content='again'))])])])
    client = NS(chat=NS(completions=NS(create=create)), close=AsyncMock())
    monkeypatch.setattr(groq, 'AsyncGroq', MagicMock(return_value=client))
    monkeypatch.setattr(settings, 'GROQ_API_KEY', 'unit-test')
    monkeypatch.setattr(settings, 'GROQ_MODEL', 'retired-model')
    discovery = AsyncMock(return_value={'chat_models': ['openai/gpt-oss-20b']})
    monkeypatch.setattr(router, 'discover_models', discovery)
    assert (await router.route_inference('hello', 'Groq'))['text'] == 'OK'
    assert (await router.route_inference('next', 'Groq'))['text'] == 'again'
    assert [c.kwargs['model'] for c in create.call_args_list] == ['retired-model', 'openai/gpt-oss-20b', 'openai/gpt-oss-20b']
    discovery.assert_awaited_once()
    assert router._model_override.get() is None
    assert settings.GROQ_MODEL == 'retired-model'


@pytest.mark.asyncio
async def test_model_recovery_is_bounded_and_does_not_retry_auth(monkeypatch):
    monkeypatch.setattr(settings, 'MODEL_FALLBACK_ENABLED', False)
    discovery = AsyncMock(return_value={'chat_models': ['openai/gpt-oss-20b']})
    monkeypatch.setattr(router, 'discover_models', discovery)
    calls = []
    @router.bounded('Groq')
    async def fail(*args):
        calls.append(router._model('Groq'))
        router._failure('Groq', NS(status_code=404))
    monkeypatch.setattr(router, 'generate_groq', fail)
    monkeypatch.setattr(settings, 'GROQ_MODEL', 'old')
    assert (await router.route_inference('hello', 'Groq'))['unavailable']
    assert len(calls) == 2
    assert not router._recovered_models
    discovery.reset_mock()
    @router.bounded('Groq')
    async def unauthorized(*args):
        router._failure('Groq', NS(status_code=401))
    monkeypatch.setattr(router, 'generate_groq', unauthorized)
    assert (await router.route_inference('hello', 'Groq'))['unavailable']
    discovery.assert_not_awaited()


@pytest.mark.parametrize('provider,entry,expected', [
    ('Groq', {'id':'openai/gpt-oss-20b', 'output_modalities':['text']}, True),
    ('Groq', {'id':'openai/gpt-oss-safeguard-20b', 'output_modalities':['text']}, False),
    ('Groq', {'id':'speech-model', 'output_modalities':['speech']}, False),
    ('NVIDIA', {'id':'nvidia/nemotron-3.5-lightning-30b-a3b'}, True),
    ('NVIDIA', {'id':'nvidia/nemotron-3.5-embed-1b'}, False),
    ('Gemini', {'name':'models/gemini-flash-latest','supportedGenerationMethods':['generateContent']}, True),
    ('Gemini', {'name':'models/gemini-image','supportedGenerationMethods':['generateContent']}, False),
])
def test_recovery_uses_only_chat_candidates(provider, entry, expected):
    assert router._chat_model(provider, entry) is expected


@pytest.mark.asyncio
async def test_orb_voice_request_recognizes_and_dispatches(monkeypatch):
    import backend.session as sessions
    ws = NS(send_json=AsyncMock())
    session = Session(ws, asyncio.Lock())
    recognize = AsyncMock(return_value={'success': True, 'transcript': 'hello nova'})
    orchestrate = AsyncMock(return_value={'status':'SUCCESS', 'response':'Hello'})
    monkeypatch.setattr(sessions.voice_input_manager, 'listen_and_recognize', recognize)
    monkeypatch.setattr(sessions, 'orchestrate_task', orchestrate)
    monkeypatch.setattr(session, 'finish', AsyncMock())
    await session.dispatch({'type':'START_LISTENING', 'payload':{'model':'auto','speech_enabled':False}})
    await session.worker
    recognize.assert_awaited_once()
    assert orchestrate.call_args.args[0] == 'hello nova'
    events = [c.args[0] for c in ws.send_json.call_args_list]
    assert any(e['type'] == 'STATE_CHANGE' and e['payload']['status'] == 'LISTENING' for e in events)
    assert any(e['type'] == 'TRANSCRIPT' and e['payload']['text'] == 'hello nova' for e in events)
    assert not session.desktop_lock.locked()
