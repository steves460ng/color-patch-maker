"""Command-line interface."""
from color_patch_maker.engine.messages import t, EngineError
import argparse
import json
import sys
from color_patch_maker.engine import layout, template_values
from color_patch_maker.engine.pdf import export, verify


def main(argv=None):
    parser = argparse.ArgumentParser(prog='cpm')
    commands = parser.add_subparsers(dest='command', required=True)
    for mode in ('grid', 'ramp'):
        p = commands.add_parser(mode)
        p.add_argument('--template', default='default', help=t('cli.template_help', 'en'))
        p.add_argument('--paper', nargs=2)
        p.add_argument('--margin')
        p.add_argument('--gap')
        p.add_argument('--patch-size')
        p.add_argument('--cols')
        p.add_argument('--out-dir', default='output')
        if mode == 'grid':
            p.add_argument('--cmyk', nargs=4, required=True)
            p.add_argument('--channels', default='CM')
            p.add_argument('--step', default=1)
            p.add_argument('--rows', default=7)
        else:
            p.add_argument('--from', dest='start', nargs=4, required=True)
            p.add_argument('--to', dest='end', nargs=4, required=True)
            p.add_argument('--count', required=True)
    p = commands.add_parser('verify')
    p.add_argument('pdf')
    p.add_argument('manifest')
    args = vars(parser.parse_args(argv))
    command = args.pop('command')
    try:
        if command == 'verify':
            verify(args['pdf'], args['manifest'])
            result = {'verified': True}
        else:
            out_dir = args.pop('out_dir')
            defaults = template_values(args.pop('template'))
            for key, value in defaults.items():
                if args[key] is None:
                    args[key] = value
            document = layout(command, **args)
            for warning in document['warnings']:
                print(warning.render('en'), file=sys.stderr)
            result = {'files': export(document, out_dir)}
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except Exception as exc:
        print(t('cli.error', 'en', error=exc.render('en') if isinstance(exc, EngineError) else str(exc)), file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
