from batch import BatchExecutor


def test_batch_executor_retry(capsys):
    calls = {'b': 0}

    def task_ok():
        pass

    def task_retry():
        calls['b'] += 1
        if calls['b'] < 2:
            raise RuntimeError('fail once')

    def task_fail():
        raise RuntimeError('always fail')

    executor = BatchExecutor([task_ok, task_retry, task_fail], max_retries=1)
    report = executor.run()
    out = capsys.readouterr().out.replace('\r', '\n')
    lines = [ln for ln in out.splitlines() if ln.strip()]
    assert '3/3' in lines[-1]
    assert 'ETA' in lines[-1]
    assert report['total'] == 3
    assert report['succeeded'] == 2
    assert report['failed'] == 1
    assert report['retries'] == 2
