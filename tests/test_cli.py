from cache_lens import cli


def test_help_exits_zero(capsys):
    assert cli.main([]) == 0
    assert "cache-lens" in capsys.readouterr().out


def test_run_unimplemented_exits_cleanly(capsys):
    rc = cli.main(["run", "echo", "hi"])
    assert rc == 2
    err = capsys.readouterr().err
    assert "not implemented" in err
    assert "wrap" in err


def test_unknown_command_exits_two(capsys):
    assert cli.main(["bogus"]) == 2
