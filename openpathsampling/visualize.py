import svgwrite as svg
from svgwrite.container import Group
import openpathsampling as paths

import json
from collections import namedtuple, OrderedDict, Counter

import openpathsampling.pathmover as pm


# TODO: Move TreeRenderer and Builder to a different file ???

class TreeRenderer(svg.Drawing):
    """
    Helper Class to render SVG Drawings

    Main use is that it is difficult to scale coordinates in SVG
    without distort the content. What we want is to move objects further
    apart of close while maintaining their size.
    """
    def __init__(self, css_style=''):
        super(TreeRenderer, self).__init__()
        self.scale_x = 20.0
        self.scale_y = 20.0

        # Add the CSS Stylesheet
        self.css_style = css_style
        self.defs.add(self.style(
            self.css_style
        ))
        self.horizontal_gap = 0.05

    @staticmethod
    def css_class(css_class):
        """
        Generate a string that can be passed to the SVG class attribute

        Parameters
        ----------
        css_class : list of str
            the class names as a list

        Returns
        -------
        str
            the actual string
        """
        return ' '.join(css_class)

    def x(self, x):
        return self.w(x)

    def y(self, y):
        return self.h(y)

    def w(self, y):
        return self.scale_x * y

    def h(self, y):
        return self.scale_y * y

    def xy(self, x, y):
        return self.x(x), self.y(y)

    def wh(self, w, h):
        return self.w(w), self.h(h)

    def connector(self, x, y, text="", css_class=None):
        if css_class is None:
            css_class = list()

        css_class += ['connector']

        return self.block(x, y, text, False, False, False, False, css_class=css_class)

    def block(self, x, y, text="",
              extend_right=True, extend_left=True,
              extend_top=False, extend_bottom=False,
              w=1.0, color=None, css_class=None, data=None):

        if css_class is None:
            css_class = list()

        css_class += ['block']

        padding = self.horizontal_gap

        group = self.g(
            class_=self.css_class(css_class)
        )

        if color is not None:
            adds = {'fill': color}
        else:
            adds = {}

        if data is not None:
            group.set_desc(desc=json.dumps(data))

        group.add(self.rect(
            insert=self.xy(x - 0.5 + padding, y - 0.3),
            size=self.wh(1.0 * w - 2 * padding, 0.6),
            **adds
        ))

        if extend_left:
            group.add(self.circle(
                center=self.xy(x - 0.5, y),
                r=self.w(padding)
            ))
        if extend_right:
            group.add(self.circle(
                center=(self.xy(x + w - 0.5, y)),
                r=self.w(padding)
            ))

        if extend_top:
            group.add(self.circle(
                center=self.xy(x, y - 0.3),
                r=self.w(padding)
            ))
        if extend_bottom:
            group.add(self.circle(
                center=(self.xy(x + w - 1.0, y + 0.3)),
                r=self.w(padding)
            ))

        group.add(self.text(
            text=str(text),
            insert=self.xy(x + (w - 1.0) / 2.0, y)
        ))

        return group

    def horizontal_region(self, x, y, w=1.0, text="",
                          extend_right=False, extend_left=False, css_class=None):

        if css_class is None:
            css_class = list()

        css_class += ['h-region']

        if w == 0:
            return []

        padding = self.horizontal_gap

        group = Group(
            class_=self.css_class(css_class)
        )

        group.add(self.line(
            start=self.xy(x - 0.5 + padding, y),
            end=self.xy(x - 0.5 + w - padding, y)
        ))

        if extend_left:
            group.add(self.circle(
                center=self.xy(x - 0.5, y),
                r=self.w(padding)
            ))
            group.add(self.line(
                start=self.xy(x - 0.5, y - 0.3),
                end=self.xy(x - 0.5, y + 0.3)
            ))

        if extend_right:
            group.add(self.circle(
                center=(self.xy(x + w - 0.5, y)),
                r=self.w(padding)
            ))
            group.add(self.line(
                start=self.xy(x + w - 0.5, y - 0.3),
                end=self.xy(x + w - 0.5, y + 0.3)
            ))

        text = str(text)

        if self.w(w) < len(text) * 5:
            text = text[0]

        if self.w(w) < 10:
            text = ''

        group.add(self.text(
            text=str(text),
            insert=self.xy(x + (w - 1.0) / 2.0, y),
            class_='shadow'
        ))
        group.add(self.text(
            text=str(text),
            insert=self.xy(x + (w - 1.0) / 2.0, y)
        ))

        return group

    def vertical_region(self, x, y, w=1.0, text="", extend_top=True, extend_bottom=True, css_class=None):
        if css_class is None:
            css_class = list()

        css_class += ['v-region']

        padding = self.horizontal_gap
        width = 0.2
        gap = 0.0

        group = Group(
            class_=self.css_class(css_class)
        )

        group.add(self.line(
            start=self.xy(x, y - 0.5 + gap),
            end=self.xy(x, y + w - 1 + 0.5 - gap)
        ))

        if extend_top:
            group.add(self.circle(
                center=self.xy(x, y - 0.5 + gap),
                r=self.w(padding)
            ))
            group.add(self.line(
                start=self.xy(x - 1.0 * width, y - 0.5 + gap),
                end=self.xy(x + width, y - 0.5 + gap)
            ))

        if extend_bottom:
            group.add(self.circle(
                center=(self.xy(x, y + (w - 1.0) + 0.5 - gap)),
                r=self.w(padding)
            ))
            group.add(self.line(
                start=self.xy(x - 1.0 * width, y + w - 1.0 + 0.5 - gap),
                end=self.xy(x + width, y + w - 1.0 + 0.5 - gap)
            ))

        group.add(self.text(
            text=str(text),
            insert=self.xy(x - width, y + (w - 1.0) / 2.0)
        ))

        return group

    def shade(self, x, y, w, css_class=None, color=None):
        if css_class is None:
            css_class = list()

        css_class += ['shade']

        adds = {}

        if color is not None:
            adds = {'fill': color}

        group = self.g(
            class_=self.css_class(css_class)
        )

        group.add(self.rect(
            insert=self.xy(x - 0.6, y + 0.10),
            size=self.wh(w + 0.2, 0.25),
            fill='white'
        ))

        group.add(self.rect(
            insert=self.xy(x - 0.6, y - 0.35),
            size=self.wh(w + 0.2, 0.25),
            fill='white'
        ))

        group.add(self.rect(
            insert=self.xy(x - 0.5, y + 0.15),
            size=self.wh(w, 0.15),
            **adds
        ))

        group.add(self.rect(
            insert=self.xy(x - 0.5, y - 0.30),
            size=self.wh(w, 0.15),
            **adds
        ))

        return group

    def vertical_connector(self, x, y1, y2, css_class=None):
        if css_class is None:
            css_class = list()

        css_class += ['v-connector']

        padding = self.horizontal_gap

        return self.line(
            class_=self.css_class(css_class),
            start=self.xy(x - 0.5, y1 + padding),
            end=self.xy(x - 0.5, y2 - padding)
        )

    def vertical_hook(self, x1, y1, x2, y2, css_class=None):
        if css_class is None:
            css_class = list()

        css_class += ['v-hook']

        padding = self.horizontal_gap

        return self.line(
            class_=self.css_class(css_class),
            start=self.xy(x1, y1 + padding + 0.3),
            end=self.xy(x2, y2 - padding - 0.3)
        )

    def horizontal_connector(self, x1, x2, y, css_class=None):
        if css_class is None:
            css_class = list()

        css_class += ['h-connector']

        padding = self.horizontal_gap

        return self.line(
            class_=self.css_class(css_class),
            start=self.xy(x1 + 0.5 + padding, y),
            end=self.xy(x2 - 0.5, y)
        )

    def label(self, x, y, text, css_class=None):
        if css_class is None:
            css_class = list()

        css_class += ['label']

        group = self.g(
            class_=self.css_class(css_class)
        )

        group.translate(self.x(x), self.y(y))

        group2 = self.g(
            class_='shift'
        )

        group2.add(
            self.text(
                text=str(text),
                insert=(0, 0)
            )
        )

        group.add(
            group2
        )

        return group

    def vertical_label(self, x, y, text, css_class=None):
        if css_class is None:
            css_class = list()

        css_class += ['v-label']

        group = self.g(
            class_=self.css_class(css_class)
        )

        group.translate(x, y)

        group.add(
            self.text(
                text=str(text),
                insert=(0, 0),
            )
        )

        return group

    def rectangle(self, x, y, w, h, css_class=None):
        if css_class is None:
            css_class = list()

        return self.rect(
            class_=self.css_class(css_class),
            insert=self.xy(x, y),
            size=self.wh(w, h),
        )

    def to_svg(self):
        return self.tostring()

    def to_html(self):
        svg_source = self.to_svg()
        html = '<!DOCTYPE html><html style="margin:0px; padding:0px; width:100%;">' + \
               svg_source + '<body style="margin:0px; padding:0px;"></body></html>'

        return html

    def _height(self):
        return self.h(self.height) + self.margin * 2

    def _width(self):
        return self.w(self.width) + self.margin * 2


class Builder(object):
    """
    Abstract class of building SVG representations
    """
    def __init__(self, additional_option_categories=None):
        options = ['analysis', 'css', 'ui', 'format']
        if additional_option_categories is not None:
            options += additional_option_categories

        option_tuple_class = namedtuple(
            'optionstuple',
            ' '.join(options)
        )

        self.options = option_tuple_class(**{opt: {} for opt in options})

    def svg(self):
        return self.render().tostring()

    def html(self):
        return self.render().tostring()

    def render(self):
        """
        Create the graphics object

        Returns
        -------
        `class`:TreeRenderer
            the rendering object that can return the final graphics
        """
        raise NotImplemented('This is a stub class. Use a derived instance!')


class MoveTreeBuilder(Builder):
    """
    Builder Class for creating MoveTree Visualisations

    You need to specify a :obj:`openpathsampling.PathMover` and a list of ensembles. Then it will
    display all possible steps in the pathmover and its relation to the given list of ensembles.

    This is useful to get an idea which parts of the ensemble affect which part of ensembles
    """
    def __init__(self, pathmover=None, ensembles=None, initial=None):
        super(MoveTreeBuilder, self).__init__()

        self.p_x = dict()
        self.p_y = dict()
        self.obj = list()

        self.ensembles = []
        self.pathmover = None
        self.initial = None

        self.traj_ens_x = dict()
        self.traj_ens_y = dict()

        self.traj_repl_x = dict()
        self.traj_repl_y = dict()

        self.ens_x = list()
        self.repl_x = list()

        self.css_style = vis_css
        self.options.analysis['only_canonical'] = True

        self.doc = None

        if pathmover is not None:
            self.pathmover = pathmover

        if ensembles is not None:
            self.ensembles = ensembles

        if initial is not None:
            self.initial = initial

    @staticmethod
    def from_scheme(scheme):
        """
        Initaliza a new `MoveTreeBuilder` from the date in a `MoveScheme`

        Parameters
        ----------
        scheme : :obj:`openpathsampling.MoveScheme`

        Returns
        -------
        :obj:`MoveTreeBuilder`
        """
        try:
            # inp is a move scheme
            input_ensembles = scheme.list_initial_ensembles()
        except AttributeError:
            # inp is a path mover
            # ??? this is nonsense in from_scheme, isn't it? you would get
            # error on the thing you return below ~~~DWHS
            input_ensembles = scheme.input_ensembles

        hidden = list(scheme.find_hidden_ensembles())
        # using network.all_ensembles forces a correct ordering
        return MoveTreeBuilder(
            pathmover=scheme.root_mover,
            ensembles=scheme.network.all_ensembles + hidden,
            initial=input_ensembles
        )

    @staticmethod
    def _get_sub_used(mover, replica_states, level):
        l = [(mover, level, replica_states)]
        subs = mover.sub_replica_state(replica_states)
        map(
            lambda x, y, z: l.extend(MoveTreeBuilder._get_sub_used(x, y, z)),
            mover.submovers, subs, [1 + level] * len(mover.submovers)
        )
        return l

    def render(self):
        doc = TreeRenderer(self.css_style)
        self.doc = doc

        level_y = dict()

        self.ens_x = [None] * len(self.ensembles)
        self.repl_x = [None] * len(self.ensembles)

        path = self.pathmover

        group = doc.g(
            class_='tree'
        )

        tree = path.depth_pre_order(
            lambda this: this, only_canonical=self.options.analysis['only_canonical'])
        total = len(tree)

        for yp, (level, sub_mp) in enumerate(tree):
            x_pos = - level

            sub_type = sub_mp.__class__
            sub_name = sub_type.__name__[:-5]

            if sub_type is paths.SamplePathMoveChange:
                group.add(
                    doc.block(level, yp))

                group.add(
                    doc.label(
                        x_pos,
                        yp,
                        sub_name,
                        css_class=['name'] + [sub_type.__name__]
                    )
                )
            else:
                group.add(
                    doc.block(
                        x_pos,
                        yp,
                    )
                )
                group.add(
                    doc.label(
                        x_pos,
                        yp,
                        sub_name
                    )
                )

            if level - 1 in level_y \
                    and level_y[level - 1] == yp - 1:
                group.add(
                    doc.vertical_connector(
                        x_pos + 1,
                        yp,
                        yp - 1
                    )
                )

            if level + 1 in level_y:
                del level_y[level + 1]

            if level in level_y and level_y[level]:
                group.add(
                    doc.vertical_connector(
                        x_pos + 1,
                        yp,
                        level_y[level]
                    )
                )

            level_y[level] = yp

        doc.add(group)

        group = doc.g(
            class_='ensembles'
        )

        for ens_idx, ens in enumerate(self.ensembles):
            txt = chr(ens_idx + 65)

            label = ens.name if hasattr(ens, 'name') else ens.__class__.__name__[:-8]

            group.add(
                doc.label(
                    ens_idx,
                    -1,
                    '[' + txt + '] ' + label,
                    css_class=['head']
                )
            )
            group.add(
                doc.vertical_hook(
                    ens_idx,
                    -1,
                    ens_idx,
                    total
                )
            )

        max_level = 0

        initial_rs = paths.pathmover.ReplicaStateSet.from_ensembles(self.initial)
        subs = MoveTreeBuilder._get_sub_used(self.pathmover, initial_rs, 0)

        # this checks if the mover can actually be run without problems
        # assert(Counter(dict(initial_rs)) >= self.pathmover.in_out_matrix.minimal)

        for yp, (level, sub_mp) in enumerate(
                path.depth_pre_order(
                    lambda this: this, only_canonical=self.options.analysis['only_canonical'])):
            sub = subs[yp]

            if level > max_level:
                max_level = level

            possible_input_replica_states = [Counter(dict(s)) for s in sub[2]]
            sub_io_set = sub_mp.in_out

            # minimal_input_replica_states = sub_io_set.minimal

            # in_ens = sub_mp.input_ensembles
            # out_ens = sub_mp.output_ensembles

            possible_ins = [
                i.ins for i in sub_io_set
                if any(s >= i.ins for s in possible_input_replica_states)]
            possible_outs = [
                i.outs for i in sub_io_set
                if any(s >= i.ins for s in possible_input_replica_states)]

            in_ens = reduce(lambda a, b: a | b, possible_ins, Counter())
            out_ens = reduce(lambda a, b: a | b, possible_outs, Counter())

            for ens_idx, ens in enumerate(self.ensembles):
                txt = chr(ens_idx + 65)
                show = False

                if in_ens is None or None in in_ens or ens in in_ens:
                    group.add(
                        doc.connector(
                            ens_idx,
                            yp - 0.15,
                            css_class=['input']
                        )
                    )
                    show = True

                if out_ens is None or None in out_ens or ens in out_ens:
                    group.add(
                        doc.connector(
                            ens_idx,
                            yp + 0.15,
                            css_class=['output'])
                    )
                    show = True
    
                if show:
                    group.add(
                        doc.connector(
                            ens_idx,
                            yp,
                            txt,
                            css_class=['unknown']
                        )
                    )

        group.translate(50, 0)

        doc.add(group)

        doc['class'] = 'movetree'

        left_x = -max_level * doc.scale_x - 120
        top_y = - 120
        width = len(self.ensembles) * doc.scale_x - left_x + 50
        height = (total + 1) * doc.scale_y - top_y

        # adjust view box to fit full image
        doc['viewBox'] = '%.2f %.2f %.2f %.2f' % (
            left_x,
            top_y,
            width,
            height
        )
        doc['width'] = width

        return doc


def _create_simple_legend(title, fnc):
    def _legend_fnc(self):
        doc = self.doc

        part = doc.g(class_='legend')
        part.add(
            doc.label(0, 0, title)
        )

        for pos_y, data in enumerate(self._plot_sample_list):
            sample = data['sample']
            part.add(
                doc.label(0, 1 + pos_y, str(
                    fnc(sample)))
            )

        return part
    return _legend_fnc


class PathTreeBuilder(Builder):
    """
    Builder class to visualize the time evolution of a list of samples

    This will basically create path trees as known from TIS and adding some useful
    features.

    The basic way to use it is to create a list of samples that should be visualized first.
    Then create the `PathTreeBuilder` and
    >>> tree = PathTreeBuilder.from_()
    >>> tree.samples = my_samplelist
    >>> SVG(tree.svg())

    There are a lot of options. For a full list see the tutorial on pathree visualization.

    Attributes
    ----------
    states : dict, 'svg_color': :obj:`openpathsampling.Volume`-like
        a dictionary listing a color that fulfills the SVG specification like
        `#888`, `gold` or `rgb(12,32,59)` referencing a volume like object that
        will return a bool when passed a snapshot. If true then the snapshot
        is highlighed using the given color
    op : :obj:`openpathsampling.CollectiveVariable`-like
        a function that returns a value when passed a snapshot. The value will
        be put on single snapshots.
    
    """
    def __init__(self):
        super(PathTreeBuilder, self).__init__(['movers'])
        self.obj = list()
        self.doc = None

        self.css_style = vis_css

        self.states = {}
        self.op = None

        self._generator = None
        self._plot_sample_list = None

        self.reset_options()
        self.coloring = None

    @property
    def generator(self):
        """
        :obj:`SampleList` : a `SampleList` object containing the list of samples
        to be plotted
        """
        return self._generator

    @generator.setter
    def generator(self, generator):
        self._generator = generator

    @property
    def samples(self):
        return iter(self._generator)

    def render(self):
        # make sure we are up-to-date
        self.generator.analyze()

        doc = TreeRenderer(self.css_style)
        self.doc = doc

        opts = self.options

        doc.scale_x = opts.css['scale_x']
        doc.scale_y = opts.css['scale_y']

        # TODO: Might remove this option. Could be useful for teaching purposes
        if type(opts.css['horizontal_gap']) is bool:
            doc.horizontal_gap = 0.05 if opts.css['horizontal_gap'] else 0.0
        else:
            doc.horizontal_gap = opts.css['horizontal_gap']

        matrix = self.generator.matrix

        # Loops over samples the first time to determine all necessary information

        pos_y = -1
        draw_pos_y = {}

        self._plot_sample_list = []

        for num, sample in enumerate(self.generator):

            pos_y += 1
            draw_pos_y[num] = pos_y

            info = self.generator[sample]

            mover_type = 'unknown'
            mover = sample.mover
            if mover is not None:
                mover_type = mover.__class__.__name__

            if hasattr(mover, '_visualization_class'):
                mover_type = getattr(mover, '_visualization_class')

            new_sample = info['new']
            time_direction = info['time_direction']
            level = info['level']

            bw_css_class = 'bw'
            fw_css_class = 'fw'

            view_options = {}
            view_options.update(opts.movers['default'])

            if new_sample:
                view_options_upd = opts.movers['new']
            elif mover_type in opts.movers:
                view_options_upd = opts.movers[mover_type]
            else:
                view_options_upd = opts.movers['unknown']

            view_options.update(view_options_upd)

            if view_options['hide']:
                pos_y -= 1
                draw_pos_y[num] = None
                continue

            label_position = view_options['label_position']

            if time_direction == -1:
                bw_css_class, fw_css_class = fw_css_class, bw_css_class
                label_position = 'left' if view_options['label_position'] == 'right' else 'right'

            css_class = [] + view_options['css_class']

            step_accepted = True
            move_accepted = True

            if isinstance(self.generator, SampleListGenerator):
                # we have steps available to use these to figure out, if a step was rejected
                step = self.generator.get_step(sample)
                if step is not None:
                    step_accepted = step.change.accepted

                change = self.generator.get_change(sample)
                if change is not None:
                    move_accepted = change.accepted

            if not step_accepted and opts.css['mark_transparent'] == 'rejected':
                css_class += ['rejected']

            if level > 0 and opts.css['mark_transparent'] == 'auxiliary':
                css_class += ['rejected']

            if not move_accepted and opts.css['mark_transparent'] == 'submove':
                css_class += ['rejected']

            data = {
                'sample': sample,
                'sample_idx': num,
                'css_class': css_class,
                'view_options': view_options,
                'bw_css_class': bw_css_class,
                'fw_css_class': fw_css_class,
                'label_position': label_position,
                'mover_type': mover_type,
                'mover_accepted': move_accepted,
                'step_accepted': step_accepted
            }

            self._plot_sample_list.append(data)

        # start plotting all parts from here

        tree_group = doc.g(
            class_='tree'
        )

        _doc_parts = [
            self.part_trajectory_label(),
            self.part_shooting_hooks(),
            self.part_snapshot_blocks()
        ]

        # finish snapshot block on the right

        min_x, max_x = min(matrix.matrix_x.keys()), max(matrix.matrix_x.keys())
        min_y, max_y = 0, pos_y

        tree_group.translate(32 + doc.w(1 - min_x), doc.h(1))

        for part in _doc_parts:
            tree_group.add(part)

        # +--------------------------------------------------------------------
        # +  LEGEND
        # +--------------------------------------------------------------------

        legend_group = doc.g(
            class_='legend'
        )
        # use different x-scaling for the legend
        tree_scale = opts.css['scale_x']
        doc.scale_x = 32

        # collect all parts of the legend separately
        legend_parts = []

        for part in reversed(opts.ui['legends']):
            if type(part) is str:
                method_name = 'part_legend_' + part
                if hasattr(self, method_name):
                    legend_parts.append(getattr(self, method_name)())
            else:
                legend_parts.append(part(self))

        # add all the legend parts

        for num, part in enumerate(legend_parts):
            part.translate(- doc.scale_x * num)
            legend_group.add(part)

        legend_columns = len(legend_parts)


        # +--------------------------------------------------------------------
        # +  BUILD FINAL IMAGE
        # +--------------------------------------------------------------------

        left_x = (-0.5 - legend_columns) * doc.scale_x
        width = 64 + tree_scale * (max_x - min_x + 2) - left_x
        height = doc.scale_y * (max_y + 3.0)
        top_y = -1.5 * doc.scale_y

        # build the full figure
        group_all = doc.g()
        group_all.add(tree_group)
        group_all.add(legend_group)

        # INFO BOX PER SNAPSHOT (still experimental)

        if opts.ui['info']:
            group_all.add(self.part_info_box())

        group_all.add(self.part_hovering_blocks(left_x, width))

        zoom = opts.css['zoom']
        group_all.scale(zoom)

        doc.add(group_all)

        # set the overall OPS tree class
        doc['class'] = 'opstree'

        # adjust view box to fit full image
        doc['viewBox'] = '%.2f %.2f %.2f %.2f' % (
            left_x * zoom,
            top_y * zoom,
            width * zoom,
            height * zoom
        )

        # set width
        w_opt = opts.css['width']
        if w_opt == 'inherit':
            # inherit will use the actual size in pixels
            doc['width'] = width * zoom
        else:
            doc['width'] = w_opt

        return doc

    def part_hovering_blocks(self, left, width):
        doc = self.doc
        group = doc.g()

        # +--------------------------------------------------------------------
        # +  HOVERING TABLE LINE PLOT
        # +--------------------------------------------------------------------

        css_class = ['tableline']

        for pos_y, data in enumerate(self._plot_sample_list):
            group.add(
                doc.rect(
                    class_=doc.css_class(css_class),
                    insert=(left, doc.y(1 + pos_y - 0.45)),
                    size=(width, doc.scale_y * 0.9)
                )
            )

        return group

    def part_trajectory_label(self):
        doc = self.doc
        group = doc.g()

        trj_format = self._create_naming_function(self.options.format['trajectory_label'])

        for pos_y, data in enumerate(self._plot_sample_list):
            sample = data['sample']
            info = self.generator[sample]

            shift = info['shift']
            length = info['length']

            view_options = data['view_options']
            label_position = data['label_position']
            css_class = data['css_class']

            traj_str = str(trj_format(sample.trajectory)) + view_options['suffix'].upper()

            if label_position == 'left':
                group.add(
                    doc.label(shift, pos_y, traj_str, css_class=css_class + ['left'])
                )
            elif label_position == 'right':
                group.add(
                    doc.label(shift + length - 1, pos_y, traj_str,
                              css_class=css_class + ['right'])
                )

        return group

    def part_shooting_hooks(self):
        doc = self.doc
        group = doc.g()

        draw_pos_y = {}
        matrix = self.generator.matrix

        for pos_y, data in enumerate(self._plot_sample_list):
            num = data['sample_idx']
            sample = data['sample']

            draw_pos_y[num] = pos_y

            info = self.generator[sample]

            new_sample = info['new']
            shift = info['shift']
            length = info['length']

            length_fw = info['length_fw']
            length_bw = info['length_bw']

            bw_css_class = data['bw_css_class']
            fw_css_class = data['fw_css_class']

            css_class = data['css_class']

            # SHOOTING HOOKS

            if not new_sample:
                bw_x = shift + length_bw
                fw_x = shift + length - 1 - length_fw

                if 0 < length_bw:
                    root_y = draw_pos_y.get(matrix.root(num, bw_x))

                    if root_y is not None and root_y < pos_y:
                        group.add(
                            doc.vertical_connector(
                                bw_x, root_y, pos_y,
                                css_class=css_class + [bw_css_class, 'connection'])
                        )

                if 0 < length_fw:
                    root_y = draw_pos_y.get(matrix.root(num, fw_x))

                    if root_y is not None and root_y < pos_y:
                        group.add(
                            doc.vertical_connector(
                                fw_x + 1, root_y, pos_y,
                                css_class=css_class + [fw_css_class, 'connection'])
                        )

        return group

    def part_snapshot_blocks(self):
        doc = self.doc
        group = doc.g()

        matrix = self.generator.matrix

        # TRAJECTORY PARTS

        opts = self.options

        trj_format = self._create_naming_function(opts.format['trajectory_label'])
        smp_format = self._create_naming_function(opts.format['sample_label'])
        snp_format = self._create_naming_function(opts.format['snapshot_label'])

        vis_blocks = {}

        for pos_y, data in enumerate(self._plot_sample_list):
            num = data['sample_idx']
            sample = data['sample']

            info = self.generator[sample]

            new_sample = info['new']
            shift = info['shift']
            length = info['length']

            length_fw = info['length_fw']
            length_bw = info['length_bw']
            overlap_reversed = info['overlap_reversed']

            bw_css_class = data['bw_css_class']
            fw_css_class = data['fw_css_class']

            view_options = data['view_options']

            css_class = data['css_class']

            # draw actual parts of the sample as
            # single snapshots, a block of snapshots or a line

            parts = []

            regions = {
                'bw': (0, length_bw),
                'fw': (length - length_fw, length),
                'full': (0, length),
                'overlap': (length_bw, length - length_fw),
                'reversed': (length_bw, length - length_fw),
                'new': (0, length)
            }
            css_classs = {
                'fw': [fw_css_class],
                'bw': [bw_css_class],
                'reversed': ['reversed'],
                'full': ['full'],
                'overlap': ['overlap'],
                'new': ['new']
            }

            vis_types = {
                'fw': 'new',
                'bw': 'new',
                'reversed': 'reversed',
                'full': 'full',
                'overlap': 'overlap',
                'new': 'new'
            }

            if not new_sample:
                if length_bw > 0:
                    parts.append('bw')

                if length_fw > 0:
                    parts.append('fw')

                if overlap_reversed:
                    parts.append('reversed')
                else:
                    if length_bw == 0 and length_fw == 0:
                        # all snaps are repeated so potentially treat differently
                        parts.append('full')
                    else:
                        parts.append('overlap')
            else:
                parts.append('new')

            for part in parts:
                hidden = False
                vis_type = view_options[vis_types[part]]
                add_css_class = css_classs[part]
                region = regions[part]

                if vis_type == 'line':
                    label = view_options['label'] or view_options['name']
                    group.add(
                        doc.horizontal_region(shift + region[0], pos_y, region[1] - region[0],
                                              label, css_class=css_class + add_css_class)
                    )
                elif vis_type == 'block':
                    group.add(
                        doc.block(
                            shift + region[0],
                            pos_y,
                            view_options['label'],
                            w=region[1] - region[0],
                            extend_left=False,
                            css_class=css_class + add_css_class
                        ))
                elif vis_type == 'single':
                    for pos in range(region[0], region[1]):
                        pos_x = shift + pos
                        snapshot = matrix[num, pos_x]

                        if opts.ui['info']:
                            data = {
                                'smp': smp_format(sample),
                                'snp': snp_format(snapshot),
                                'trj': trj_format(sample.trajectory)
                            }
                        else:
                            data = {}

                        txt = ''

                        if self.op is not None and opts.ui['cv']:
                            txt = str(self.op(snapshot))

                        group.add(
                            doc.block(
                                pos_x,
                                pos_y,
                                txt,
                                extend_left=pos > 0,
                                extend_right=pos < length - 1,
                                css_class=css_class + add_css_class,
                                data=data,
                                color=self.coloring(snapshot) if self.coloring else None
                            ))
                else:
                    hidden = True

                if not hidden:
                    self._update_vis_block(vis_blocks, num, shift, region)

        # STATE COLORING

        if self.states is not None:
            for color, op in self.states.iteritems():
                xp = None
                for pos_y, data in enumerate(self._plot_sample_list):
                    num = data['sample_idx']

                    left = None
                    for xp in matrix.get_x_range(num):
                        if xp in vis_blocks[num] and bool(op(matrix[num, xp])):
                            if left is None:
                                left = xp
                        else:
                            if left is not None:
                                group.add(
                                    doc.shade(left, pos_y, xp - left, color=color)
                                )
                                left = None

                    if left is not None:
                        group.add(
                            doc.shade(left, pos_y, xp - left + 1, color=color)
                        )

        return group

    def part_info_box(self):
        doc = self.doc
        group = doc.g()

        group.add(
            doc.label(0, -1, 'Information', css_class=['infobox'])
        )

        doc.defs.add(doc.script(
            content='''
               box = $('.opstree .infobox text')[0];
               var kernel = IPython.notebook.kernel;
               $('.opstree .block').each(
                function() {
                json = JSON.parse($(this)[0].firstChild.textContent);
                 $(this).data(json);
                }
               );
               $('.opstree .block').hover(
                function(){
                  box.textContent =
                  'Snapshot(' + $(this).data('snp') + ')' + ' ' +
                  'Trajectoy(' + $(this).data('trj') + ')';
                 },
                 function(){
                  box.textContent = '';
                 });
        '''))

        return group

    part_legend_ensemble = _create_simple_legend('ens', lambda sample: sample.ensemble.name)
    part_legend_replica = _create_simple_legend('repl', lambda sample: sample.replica)
    part_legend_bias = _create_simple_legend('bias', lambda sample: sample.bias)

    def part_legend_sample(self):

        doc = self.doc
        smp_format = self._create_naming_function(self.options.format['sample_label'])

        part = doc.g(class_='legend')
        part.add(
            doc.label(0, 0, 'smp')
        )

        for pos_y, data in enumerate(self._plot_sample_list):
            sample = data['sample']
            part.add(
                doc.label(0, 1 + pos_y, str(
                    smp_format(sample)))
            )

        return part

    def part_legend_correlation(self):
        doc = self.doc
        time_symmetric = self.generator.time_symmetric

        part = doc.g(class_='legend')
        part.add(
            doc.label(0, 0, 'cor')
        )

        old_tc = 1
        prev = self._plot_sample_list[0]['sample']

        for pos_y, data in enumerate(self._plot_sample_list):
            sample = data['sample']

            if pos_y > 0:
                if not paths.Trajectory.is_correlated(
                        sample.trajectory,
                        prev,
                        time_reversal=time_symmetric
                ):
                    part.add(
                        doc.vertical_region(
                            0,
                            old_tc,
                            1 + pos_y - old_tc,
                            css_class=['correlation']
                        )
                    )

                    old_tc = 1 + pos_y
                    prev = sample.trajectory

        part.add(
            doc.vertical_region(
                0,
                old_tc,
                1 + len(self._plot_sample_list) - old_tc,
                extend_bottom=False,
                css_class=['correlation']))

        return part

    def part_legend_step(self):
        doc = self.doc

        part = doc.g(class_='legend')
        part.add(
            doc.label(0, 0, 'step')
        )

        for pos_y, data in enumerate(self._plot_sample_list):
            sample = data['sample']
            if isinstance(self.generator, SampleListGenerator):
                step = self.generator.get_step(sample)
                if step is None:
                    # apparently this sample was not generate by any step we know
                    txt = '*'
                else:
                    txt = str(step.mccycle)
            else:
                txt = '?'

            part.add(
                doc.label(0, 1 + pos_y, txt)
            )

        return part

    def _create_naming_function(self, fnc):
        opts = self.options
        return fnc or opts.format['default_label'] or (lambda obj: '')

    @staticmethod
    def _update_vis_block(vis_block, pos_y, shift, region):
        # necessary to remember where we actually drew something
        if pos_y not in vis_block:
            vis_block[pos_y] = set()

        vis_block[pos_y].update(range(shift + region[0], shift + region[1] + 1))

    def use_storage_indices(self, storage):
        """
        Set the default_labelling to use indices in the given storage
        Parameters
        ----------
        storage : :obj:`openpathsampling.Storage`
            the storage to be used for indices

        """
        self.options.format['default_label'] = storage.idx

    def reset_options(self):
        """
        Return the options to default

        """
        self.options.movers.update({
            'ReplicaExchangeMover': {
                'name': 'RepEx',
                'suffix': 'x',
                'css_class': ['repex'],
                'hide': True
            },
            'BackwardShootMover': {
                'name': 'Backward',
                'suffix': 'b',
                'css_class': ['shooting']
            },
            'ForwardShootMover': {
                'name': 'Forward',
                'suffix': 'f',
                'label_position': 'right',
                'css_class': ['shooting']
            },
            'BackwardExtendMover': {
                'name': 'Extend',
                'suffix': 'b',
                'overlap': 'line',  # this will repeat the part where the extension is started
                'css_class': ['extend']
            },
            'ForwardExtendMover': {
                'name': 'Extend',
                'suffix': 'f',
                'overlap': 'line',  # this will repeat the part where the extension is started
                'label_position': 'right',
                'css_class': ['extend']
            },
            'FinalSubtrajectorySelectMover': {
                'name': 'Truncate',
                'suffix': 't',
                'label_position': 'right',
                'css_class': ['extend']
            },
            'FirstSubtrajectorySelectMover': {
                'name': 'Truncate',
                'suffix': 't',
                'css_class': ['extend']
            },
            'EnsembleHopMover': {
                'name': 'Hop',
                'suffix': 'h',
                'css_class': ['hop']
            },
            'PathReversalMover': {
                'name': 'Reversal',
                'suffix': 'r',
                'css_class': ['reversal']
            },
            'new': {
                'name': 'New',
                'suffix': '+',
                'css_class': ['unknown']
            },
            'unknown': {
                'name': '???',
                'suffix': '?',
                'css_class': ['repex']
            },
            'default': {
                'name': '---',
                'overlap': 'none',
                'new': 'block',
                'reversed': 'block',
                'full': 'line',
                'label': '',
                'suffix': '?',
                'label_position': 'left',
                'css_class': [],
                'hide': False
            }
        })
        self.options.ui.update({
            'legends': ['sample', 'correlation'],
            'cv': True,
            'info': False,
        })
        self.options.css.update({
            'scale_x': 5,
            'scale_y': 15,
            'zoom': 1.0,
            'horizontal_gap': False,
            'width': '100%',
            'mark_transparent': 'rejected'
        })
        self.options.format.update({
            'default_label': lambda x: hex(id(x))[-5:] + ' ',
            # 'default_label': lambda x: '',
            'trajectory_label': lambda x: '',
            'sample_label': None,
            'step_label': None,
            'snapshot_label': None,
            'display_repeated': True,
            'new_snapshots': True,
            'repeated_snapshots': True
        })

        if self.generator and self.generator.steps:
            self.options.ui['legends'] = ['step', 'correlation']

    def reset(self):
        """
        Revert to default options and remove all ther setting as well

        """
        self.reset_options()
        self.states = {}
        self.op = None
        self.coloring = None

        if self._generator is not None:
            self._generator.set_default_settings()


class PathTree(PathTreeBuilder):
    def __init__(self, steps, generator=None):
        super(PathTree, self).__init__()

        self.steps = steps
        self.generator = generator
        self.reset_options()

    @property
    def generator(self):
        return self._generator

    @generator.setter
    def generator(self, generator):
        self._generator = generator
        if generator is not None:
            self._generator.steps = self.steps
            self._generator.update_tree_options(self)

    @property
    def steps(self):
        return self._steps

    @steps.setter
    def steps(self, steps):
        self._steps = StepList(steps)
        if self.generator is not None:
            self.generator.steps = self.steps


class SnapshotMatrix(object):
    def __init__(self, sample_list):
        self.sample_list = sample_list
        self.matrix_x = {}
        self.matrix_y = {}
        self.shift = [0] * len(sample_list)

    @property
    def time_symmetric(self):
        return self.sample_list.time_symmetric

    def __setitem__(self, key, value):
        y_pos = key[0]
        x_pos = key[1]

        if x_pos not in self.matrix_x:
            self.matrix_x[x_pos] = {}

        if y_pos not in self.matrix_y:
            self.matrix_y[y_pos] = {}

        if isinstance(value, paths.BaseSnapshot):
            self.matrix_x[x_pos][y_pos] = value
            self.matrix_y[y_pos][x_pos] = value

        elif type(value) is paths.Trajectory:
            for pos, snapshot in enumerate(value.as_proxies()):
                self[y_pos, x_pos + pos] = snapshot

            self.shift[y_pos] = x_pos

    def __getitem__(self, item):
        y_pos = item[0]
        x_pos = item[1]
        if x_pos in self.matrix_x:
            return self.matrix_x[x_pos][y_pos]
        else:
            raise KeyError(x_pos)

    def get_x_range(self, y_pos):
        xs = set(self.matrix_y[y_pos])
        return range(min(xs), max(xs) + 1)

    def get(self, y_pos, x_pos):
        if x_pos in self.matrix_x:
            return self.matrix_x[x_pos].get(y_pos)
        else:
            return None

    def is_new(self, y_pos, x_pos):
        snapshot = self[y_pos, x_pos]

        x = self.matrix_x[x_pos]

        pos = y_pos
        while pos > 0:
            new_y_pos = self.sample_list.parent(pos)

            if not new_y_pos or new_y_pos > pos:
                return True

            pos = new_y_pos

            if snapshot == x[pos]:
                return False

        return True

    def _snapshot_is(self, snap1, snap2):
        if not self.time_symmetric:
            return snap1 == snap2
        else:
            if snap1 == snap2:
                return True
            else:
                return snap1.reversed == snap2

    def root(self, y_pos, x_pos):
        snapshot = self[y_pos, x_pos]

        x = self.matrix_x[x_pos]

        pos = y_pos
        while pos > 0:
            new_y_pos = self.sample_list.parent(pos)
            if new_y_pos is None or new_y_pos > pos:
                return pos

            if new_y_pos not in x or not self._snapshot_is(snapshot, x[new_y_pos]):
                return pos

            pos = new_y_pos

        return pos

    def parent(self, y_pos, x_pos):
        snapshot = self[y_pos, x_pos]

        x = self.matrix_x[x_pos]

        if y_pos == 0:
            return None

        new_y_pos = self.sample_list.parent(y_pos)

        if new_y_pos is None or new_y_pos > y_pos:
            return None

        if not self._snapshot_is(snapshot, x[new_y_pos]):
            return None

        return new_y_pos


class SampleSelector(object):
    """
    A Function that can construct a series of samples within the scope of a list of MC steps

    If you want to plot a list of samples and study their evolution you usually do that within
    the context of MC steps they were generated in. You do not have to because you can generate
    samples without a step, but that is rather the exception. Therefore you construct the
    PathTreeBuilder with a list of steps as basis.

    To select the way in which you want to pick a list of samples from the ones appearing in
    these steps you use a SampleSelector, like `ReplicaEvolution(replica_id, accepted)`,
    `SampleAncestors(child_sample)`, `EnsembleEvolution(ensemble, accepted)`
    """


class SampleList(OrderedDict):
    """
    A timely ordered series of `Sample` objects.

    This is effectively a list object enhanced with a few additional functions that
    simplify analysis. Although this can hold an arbitrary list of samples it is meant
    to represent a time evolution of samples and thus samples that have a causal relation.

    Examples would be the history of samples that lead to a specific samples (heritage)
    or the history of samples in a specific ensemble or of a given replica.

    It provides some useful filters that make sense for samples. And you can add a list of
    steps as context, where the samples where generated in. I analyzing the evolution of a
    path you do not need the context. It is mostly for error checking and inspecting moves,
    while analyzing in the step context allow you to analyze decorrelation of paths.

    Attributes
    ----------
    time_symmetric : bool, default: `True`
        if `True` a snapshots and its reversed counterpart will be treated alike.
    flip_time_direction : bool, default: `False`
        if `True` the sample list detects if a reversal happens between to successive
        samples and will reverse the time direction to counter the flip. This results in
        a much clearer picture and shows the redundancy of snapshots when reversing
        trajectories. Use with care it will distort the sense of time from left to right
        in the generated picture
    trace_missing : bool, default: `False`
        if `True` this will mean that alignment between trajectories will be traced using
        the `.parent` property even if a sample is not contained in the sample list itself.
        Imagine you are looking only at the evolution of a particular replica after a
        complete MC step. These steps might involve several shooting moves that will
        completely deorrelate between a sample and its listed predecessor. Usually the closest
        parent is used as a reference and overlapping parts will be aligned. If the closest
        parent does not have overlap (because of being completely decorrelated) we cannot simply
        align. In that case you might create a new hidden samplelist tracing the parents to
        the closest parent to determine the relative shift. This is done, if `trace_missing` is
        `True`. If `False` two such samples will be treated as unrelated and the new is placed at
        position zero as is the very first sample in the list.

        Notes
        -----
        This is a special `OrderedDict` of the form `{ samp1: information, samp2: information }`.
        So, if you get by integer you will get the sample at the position, while getting a
        sample directly will act as a regular dict. So this will actually work and return the
        information of the third sample in the list.

        >>> sl = SampleList()
        >>> print sl[sl[3]]

        It seemed to make sense to provide a possibility to access a specific index in an
        OrderedDict, which is not possible in the base implementation.

    """

    def __init__(
            self,
            samples,
            time_symmetric=True,
            flip_time_direction=False,
            trace_missing=False
    ):
        OrderedDict.__init__(self)

        self._time_symmetric = time_symmetric
        self._flip_time_direction = flip_time_direction
        self._trace_missing = trace_missing

        self._matrix = []
        self._steps = None

        if hasattr(samples, '__iter__'):
            for s in samples:
                self[s] = {}
        else:
            self[samples] = {}

        self.analyze()

    def set_default_settings(self):
        self._time_symmetric = True
        self._flip_time_direction = False
        self._trace_missing = False

        self.analyze()

    def filter(self, filter_func):
        """
        Keep only samples where the filter function returns True

        Parameters
        ----------
        filter_func : callable
            a function that is called on all sample, data pairs. If `True` is returned the
            sample is kept, otherwise the sample will be removed from the list. The function
            can be called with either `filter_func(sample, data_dict)` or `filter_func(sample),
            depending on how many parameters the function accepts. data dict is the information
            contained in `sample_list[sample]`

        """
        try:
            # see, if the filter function accepts two parameters
            self.set_samples([
                samp for samp, data in self.iteritems() if filter_func(samp, data)
            ])
        except:
            self.set_samples([
                samp for samp in self if filter_func(samp)
            ])

    @property
    def steps(self):
        """
        list of `openpathsampling.MCStep` : The list of steps giving the context for the samples.
            Currently samples do no contain information about the context / step they were
            generated in.

        """
        return self._steps

    @steps.setter
    def steps(self, value):
        self._steps = value

    @staticmethod
    def filter_redundant_moves(samp, data):
        """
        A filter letting only samples pass that are not identical to the previous one
        """
        return not data['length'] == data['length_shared']

    @property
    def matrix(self):
        """
        :obj:`SnapshotMatrix`
            a generated sparse matrix of snapshots. Mostly used for plotting purposes
        """
        return self._matrix

    def set_samples(self, samples):
        """

        Parameters
        ----------
        samples : list of :obj:`openpathsampling.Sample`
            the list of samples to be inspected. This will trigger reevaluation of the
            current list of samples

        """
        self.clear()
        for s in samples:
            self[s] = {}

        self.analyze()

    @staticmethod
    def from_ancestors(sample):
        """
        Generate a :obj:`SampleList` from the ancestors of a given sample

        Parameters
        ----------
        sample : :obj:`openpathsampling.Sample`
            the sample from which the ancestory are traced. It will follow the `.parent`
            property until no parent is found

        Returns
        -------
        :obj:`SampleList`
            the generated list of samples

        """

        l = []

        while sample is not None:
            l.append(sample)
            sample = sample.parent

        return SampleList(reversed(l))

    @staticmethod
    def from_steps(steps, replica, accepted):
        """
        Generate a :obj:`SampleList` from a list of step and a replica ID

        Parameters
        ----------
        steps : list of :obj:`openpathsampling.MCStep`
            the list of simulation steps to be inspected and turned into a
            list of samples
        replica : int
            the replica ID to be traced
        accepted : bool
            if `True` only accepted samples will be included in the list.
            Otherwise it will also contain trial samples

        Returns
        -------
        :obj:`SampleList`
            the generated list of samples

        """
        sl = SampleList(SampleList._get_samples_from_steps(steps, replica, accepted))
        sl.steps = steps
        return sl

    @staticmethod
    def _get_samples_from_steps(steps, replica, accepted):
        if accepted:
            samp = steps[-1].active[replica]
            samples = [samp]
            while samp.parent is not None:
                samp = samp.parent
                samples.append(samp)

            return list(reversed(samples))
        else:
            samp = steps[0].active[replica]
            samples = [samp]
            for step in steps:
                rep_trials = [s for s in step.change.trials
                              if s.replica == replica]
                if len(rep_trials) > 0:
                    samples.append(rep_trials[-1])

            return samples

    def without_redundant(self):
        """
        Remove all redundant samples and return a new object

        Redundant samples are samples where the overlap with the previous sample is effectively
        all samples. This depends on the analysis settings like `time_symmetric` and `flip_time_direction`

        Returns
        -------
        :obj:`SampleList`
            the generated list of samples


        """
        l = SampleList(
            [samp for samp, data in self.iteritems() if data['length_shared'] < data['length']]
        )
        l.flip_time_direction = self.flip_time_direction
        l.time_symmetric = self.time_symmetric
        return l

    def remove_redundant(self):
        """
        Remove all redundant samples from the current object.

        Redundant samples are samples where the overlap with the previous sample is effectively
        all samples. This depends on the analysis settings like `time_symmetric` and `flip_time_direction`

        """
        l = [samp for samp, data in self.iteritems() if data['length_shared'] < data['length']]
        self.set_samples(l)

    def flatten_to_main(self):
        """
        Remove all redundant samples from the current object.

        Redundant samples are samples where the overlap with the previous sample is effectively
        all samples. This depends on the analysis settings like `time_symmetric` and `flip_time_direction`

        """
        l = [samp for samp, data in self.iteritems() if data['level'] == 0]
        self.set_samples(l)

    @property
    def time_symmetric(self):
        return self._time_symmetric

    @time_symmetric.setter
    def time_symmetric(self, value):
        self._time_symmetric = value
        self.analyze()

    @property
    def flip_time_direction(self):
        return self._flip_time_direction

    @flip_time_direction.setter
    def flip_time_direction(self, value):
        self._flip_time_direction = value
        self.analyze()

    @property
    def trace_missing(self):
        return self._trace_missing

    @trace_missing.setter
    def trace_missing(self, value):
        self._trace_missing = value
        self.analyze()

    def __getitem__(self, item):
        if type(item) is slice:
            return SampleList(self.keys()[item])
        elif isinstance(item, list):
            return [self[s] for s in item]
        elif type(item) is int:
            return self.keys()[item]
        else:
            return OrderedDict.__getitem__(self, item)

    def index(self, value):
        """
        Return the index of a sample in the list

        Parameters
        ----------
        value : :obj:`openpathsampling.Sample`

        Returns
        -------
        int
            the index if present in the list. Throw an exception otherwise
        """
        return self.keys().index(value)

    def parent(self, idx):
        """
        Return the index of the next present parent of an index or sample

        Next present parent means. That from the given sample we check if the
        direct parent is in the list. If so its index is returned. If not we
        try recursively of the parent of the parent and so on until we find
        a sample that is present or return None

        Parameters
        ----------
        idx : :obj:`openpathsampling.Sample` or int
            If an `int` is given the Sample at the index in the list is used,
            othewise the sample is used for finding the parent

        Returns
        -------
        int or None
            the index of the parent in the list if present. None otherwise.
        """
        try:
            if type(idx) is int:
                samp = self[idx]
            else:
                samp = idx

            parent = samp.parent
            while parent not in self and parent is not None:
                parent = parent.parent

            return self.keys().index(parent)

        except ValueError:
            return None

    def _trajectory_index(self, trajectory, snapshot):
        if self.time_symmetric:
            return trajectory.index_symmetric(snapshot)
        else:
            return trajectory.index(snapshot)

    def _trajectory_contains(self, trajectory, snapshot):
        if self.time_symmetric:
            return trajectory.contains_symmetric(snapshot)
        else:
            return snapshot in trajectory

    def analyze(self):
        """
        Perform the analysis of the samples.

        It will loop through the list of samples and determine the overlap with its
        parent. Note that at this point there is no move that can create a sample from
        more than one initial one. So it is enough to assume that a sample has a single
        parent, its origin that is determined by the mover.

        Since the parent is unique we will base the alignment upon the position of the
        parent or (if samples are missing) on the closest ancestor.
        The alignment will be chosen such that parts that exist in both trajectories are
        placed on top. If we chose `time_symmetric` this will also be true if the trajectories
        are reversed.

        If you set `flip_time_direction = True` samples might be displayed in reverse order
        to perfectly align reversed ones. This means that in a plot the direction of time
        but not of correlation will change. Imagine have samples between state A and B and
        you start with A -> B then this will keep the initial direction in a plot although
        a time reversal move will go from B -> A while being perfectly reversed.

        Should be called automatically when relevant changes are detected.
        """
        matrix = SnapshotMatrix(self)
        flip_time_direction = self.flip_time_direction
        parent = None
        time_direction = +1

        for y_pos, sample in enumerate(self):
            traj = sample.trajectory
            length = len(traj)
            parent_shift = 0
            parent_traj = None
            overlap = None

            if sample.parent is not None:
                parent = sample.parent

            if parent not in self:
                while parent not in self and parent is not None:
                    parent = parent.parent

                if parent is None:
                    time_direction = +1

            if parent is not None:
                parent_shift = self[parent]['shift']
                time_direction = self[parent]['time_direction']

                parent_traj = parent.trajectory

                if time_direction == -1:
                    traj = paths.Trajectory(list(reversed(traj.as_proxies())))
                    parent_traj = paths.Trajectory(list(reversed(parent_traj.as_proxies())))

                overlap = parent_traj.shared_subtrajectory(traj, time_reversal=self.time_symmetric)
                overlap_length = len(overlap)

            if overlap is None or len(overlap) == 0:
                # no overlap so we need to start new
                if not self.trace_missing:
                    traj_shift = 0
                elif parent is not None:
                    # if a parent is present but no overlap we could trace the missing chain
                    # and use this shift. This is "expensive" so by default it is switched off

                    current = paths.Sample(
                        replica=sample.replica,
                        trajectory=traj,
                        ensemble=sample.ensemble,
                        bias=sample.bias,
                        details=sample.details,
                        parent=sample.parent,
                        mover=sample.mover
                    )

                    parent_list = [current]
                    while current is not parent and current is not None:
                        current = current.parent
                        parent_list.append(current)

                    if current is None:
                        # cannot trace to actual parent. That should not be possible since previously
                        # we found a parent. So just to make sure
                        traj_shift = 0
                    else:
                        missing_sl = SampleList(
                            reversed(parent_list),
                            time_symmetric=self.time_symmetric,
                            flip_time_direction=self.flip_time_direction,
                            trace_missing=False
                        )

                        traj_shift = parent_shift + missing_sl[missing_sl.last]['shift']

                else:
                    traj_shift = 0

                self[sample] = {
                    'shift': traj_shift,
                    'new': True,
                    'time_direction': time_direction,
                    'correlation': 0.0,
                    'length': len(traj),
                    'level': 0,
                    'length_shared': 0,
                    'length_fw': 0,
                    'length_bw': 0,
                    'overlap_reversed': False
                }
            else:
                new_fw = self._trajectory_index(traj, overlap.get_as_proxy(-1))
                new_bw = self._trajectory_index(traj, overlap.get_as_proxy(0))

                overlap_reversed = False

                if new_bw > new_fw:
                    overlap_reversed = True

                    new_fw, new_bw = new_bw, new_fw

                    if flip_time_direction:
                        # reverse the time and adjust the shifting

                        traj = paths.Trajectory(list(reversed(traj.as_proxies())))
                        time_direction *= -1
                        overlap_reversed = False
                        new_fw, new_bw = length - 1 - new_bw, length - 1 - new_fw

                    else:
                        # after
                        overlap_length = 0

                traj_shift = parent_shift + self._trajectory_index(parent_traj, overlap.get_as_proxy(0)) - new_bw

                self[sample] = {
                    'shift': traj_shift,
                    'length_fw': length - 1 - new_fw,
                    'length_bw': new_bw,
                    'length_shared': overlap_length,
                    'length': length,
                    'overlap_reversed': overlap_reversed,
                    'new': False,
                    'time_direction': time_direction,
                    'correlation': (1.0 * overlap_length) / len(traj),
                    'parent_y': self.parent(sample),
                    'level': 0
                }

            matrix[y_pos, traj_shift] = traj

            parent = sample

        self._matrix = matrix

        for sample in reversed(self):
            pos_y = self.index(sample)
            pos_parent = self.parent(sample)
            if pos_parent is not None and pos_parent < pos_y - 1:
                for pos in range(pos_parent + 1, pos_y):
                    self[self[pos]]['level'] += 1

    @property
    def correlation(self):
        """
        Return a list of correlation between neighboring samples in the list

        The correlation is the fraction of shared snapshots. If `time_symmetric` is set
        then this is taken into account and reversing of snapshots is ignored.

        Returns
        -------
        list of float
            the list of correlations

        """
        return [s['correlation'] for s in self.values()]

    @property
    def decorrelated_trajectories(self):
        """List of decorrelated trajectories from the internal samples.

        In path sampling, two trajectories are said to be "decorrelated" if
        they share no frames in common. This is particularly important in
        one-way shooting. This function returns the list of trajectories,
        making the number (i.e., the length of the list) also easily
        accessible.

        Note that this only traced the main path of samples. So if you have
        e.g. rejected parts these will not be taken into account.

        Returns
        -------
        list of :obj:`opnpathsampling.Trajectory`
        """

        return [samp.trajectory for samp in self.decorrelated]

    @property
    def decorrelated(self):
        """List of decorrelated samples from the internal samples.

        In path sampling, two trajectories are said to be "decorrelated" if
        they share no frames in common. This is particularly important in
        one-way shooting. This function returns the list of trajectories,
        making the number (i.e., the length of the list) also easily
        accessible.

        Note that this only traced the main path of samples. So if you have
        e.g. rejected parts these will not be taken into account.

        Returns
        -------
        list of :obj:`opnpathsampling.Trajectory`
        """
        prev = self[0].trajectory
        decorrelated = [self[0]]

        for s in self:
            # check if we are on the main path of evolution and not something that is rejected
            # at some point
            if self[s]['level'] == 0:
                if not s.trajectory.is_correlated(prev, self.time_symmetric):
                    decorrelated.append(s)
                    prev = s.trajectory

        return decorrelated

    @property
    def first(self):
        """
        :obj:`openpathsampling.Sample`
            Returns the first sample in the list
        """
        return self[0]

    @property
    def last(self):
        """
        :obj:`openpathsampling.Sample`
            Returns the last sample in the list
        """
        return self[-1]


class StepList(list):
    def __init__(self, steps):
        list.__init__(self, steps)

        self._create_step_sample_list()

    def _create_step_sample_list(self):
        # TODO: This will someday be replaced by a `sample.step` property
        self._sample_step_list = dict()
        self._sample_change_list = dict()
        for step in self:
            for ch in step.change:
                for s in ch.samples:
                    self._sample_step_list[s] = step
                    self._sample_change_list[s] = ch

    def get_step(self, sample):
        """
        Return the step in which a sample was generated

        Parameters
        ----------
        sample : :obj:`Sample`
            the sample to find the generating `MCStep` from

        Returns
        -------
        :obj:`MCStep`
            the step in which the sample was generated

        Notes
        -----
        A sample can appear in other moves as well, but it is uniquely generated in
        one move and thus during one step
        """

        return self._sample_step_list.get(sample)

    def get_mccycle(self, sample):
        """
        Return the MC cycle in which a sample was generated

        Parameters
        ----------
        sample : :obj:`Sample`
            the sample to find the generating `MCStep` from

        Returns
        -------
        int
            the cycle number in which the sample was generated

        """

        return self._sample_step_list.get(sample).mccycle

    def get_change(self, sample):
        """
        Return the (sub-)change in which a sample was generated

        Parameters
        ----------
        sample : :obj:`Sample`
            the sample to find the generating `MCStep` from

        Returns
        -------
        :obj:`PathMoveChange`
            the move change in which the sample was generated

        """

        return self._sample_change_list.get(sample)

    @property
    def samples(self):
        return self._sample_step_list.keys()


class SampleListGenerator(SampleList):
    """
    An ordered list of `Sample`s analyzed in the context of a list of `MCStep`s

    You often want to analyze the evolution of Replicas during a simulation. This object
    will mimick a list of Samples generated from steps to your liking
    """

    def __init__(self):
        super(SampleListGenerator, self).__init__([])
        self.steps = None

    @property
    def steps(self):
        return self._steps

    @steps.setter
    def steps(self, steps):
        self._steps = steps
        if steps is not None:
            self._update_sample()

    def _update_sample(self):
        pass

    def update_tree_options(self, tree):
        pass

    def get_mccycle(self, sample):
        """
        Return the MC cycle in which a sample was generated

        Parameters
        ----------
        sample : :obj:`Sample`
            the sample to find the generating `MCStep` from

        Returns
        -------
        int
            the cycle number in which the sample was generated

        """

        return self.steps.get_mccycle(sample)

    def get_step(self, sample):
        """
        Return the step in which a sample was generated

        Parameters
        ----------
        sample : :obj:`Sample`
            the sample to find the generating `MCStep` from

        Returns
        -------
        :obj:`MCStep`
            the step in which the sample was generated

        Notes
        -----
        A sample can appear in other moves as well, but it is uniquely generated in
        one move and thus during one step
        """

        return self.steps.get_step(sample)

    def get_change(self, sample):
        """
        Return the (sub-)change in which a sample was generated

        Parameters
        ----------
        sample : :obj:`Sample`
            the sample to find the generating `MCStep` from

        Returns
        -------
        :obj:`PathMoveChange`
            the move change in which the sample was generated

        """

        return self.steps.get_change(sample)


class ReplicaEvolution(SampleListGenerator):
    """
    An ordered list of `Sample`s analyzed in the context of a list of `MCStep`s

    You often want to analyze the evolution of Replicas during a simulation. This object
    will mimick a list of Samples generated from steps to your liking
    """

    def __init__(self, replica, accepted=True):
        super(ReplicaEvolution, self).__init__()
        self._replica = replica
        self._accepted = accepted

    def _update_sample(self):
        self.set_samples(SampleList._get_samples_from_steps(
            self.steps,
            self._replica,
            self._accepted
        ))

        self.analyze()

    @property
    def replica(self):
        return self._replica

    @replica.setter
    def replica(self, value):
        self._replica = value
        self._update_sample()

    @property
    def accepted(self):
        return self._accepted

    @accepted.setter
    def accepted(self, value):
        self._accepted = value
        self._update_sample()

    def update_tree_options(self, tree):
        tree.options.css['mark_transparent'] = 'rejected'


class SampleAncestors(SampleListGenerator):
    def __init__(self, sample):
        super(SampleAncestors, self).__init__()
        self._sample = sample

    @property
    def sample(self):
        return self._sample

    @sample.setter
    def sample(self, value):
        self._sample = value
        self._update_sample()

    def _update_sample(self):

        sample = self.sample
        l = []

        while sample is not None and (not self.steps or sample in self.steps.samples):
            l.append(sample)
            sample = sample.parent

        self.set_samples(SampleList(reversed(l)))

    def update_tree_options(self, tree):
        tree.options.css['mark_transparent'] = 'auxiliary'


class EnsembleEvolution(SampleListGenerator):
    """
    An ordered list of `Sample`s analyzed in the context of a list of `MCStep`s

    You often want to analyze the evolution of Replicas during a simulation. This object
    will mimick a list of Samples generated from steps to your liking
    """

    def __init__(self, ensemble, accepted=True):
        super(EnsembleEvolution, self).__init__()
        self._ensemble = ensemble
        self._accepted = accepted

    def _update_sample(self):
        self.set_samples([
            step.active[self.ensemble] for step in self.steps
            if not self.accepted or step.change.accepted
        ])

    @property
    def ensemble(self):
        return self._ensemble

    @ensemble.setter
    def ensemble(self, value):
        self._ensemble = value
        self._update_sample()

    @property
    def accepted(self):
        return self._accepted

    @accepted.setter
    def accepted(self, value):
        self._accepted = value
        self._update_sample()

    def update_tree_options(self, tree):
        tree.options.css['mark_transparent'] = 'rejected'


# TODO: Move this to extra file and load using 'pkgutil' or so
vis_css = r"""
.opstree text, .movetree text {
    alignment-baseline: central;
    font-size: 10px;
    text-anchor: middle;
    font-family: Futura-CondensedMedium;
    font-weight: lighter;
    stroke: none !important;
}
.opstree .block text, .movetree .block text {
    alignment-baseline: central;
    font-size: 8px;
    text-anchor: middle;
    font-family: Futura-CondensedMedium;
    font-weight: lighter;
    stroke: none !important;
}
.opstree text.shadow {
    stroke-width: 3;
    stroke: white !important;
}
.opstree .left.label .shift text {
    text-anchor: end;
}
.opstree .right.label .shift text {
    text-anchor: start;
}
.opstree .block text, .movetree .block text {
    fill: white !important;
    stroke: none !important;
}
.opstree .block {
    stroke: none !important;
}
.opstree g.block:hover rect {
    opacity: 0.5;
}
.opstree .repex {
    fill: blue;
    stroke: blue;
}
.opstree .extend {
    fill: blue;
    stroke: blue;
}
.opstree .truncate {
    fill: blue;
    stroke: blue;
}
.opstree .new {
    fill: black;
    stroke: black;
}
.opstree .unknown {
    fill: gray;
    stroke: gray;
}
.opstree .hop {
    fill: blue;
    stroke: blue;
}
.opstree .correlation {
    fill: black;
    stroke: black;
}
.opstree .shooting.bw {
    fill: green;
    stroke: green;
}
.opstree .shooting.fw {
    fill: red;
    stroke: red;
}
.opstree .shooting.overlap {
    fill: #666;
    stroke: #666;
}
.opstree .reversal {
    fill: gold;
    stroke: gold;
}
.opstree .virtual {
    opacity: 0.1;
    fill:gray;
    stroke: none;
}
.opstree line {
    stroke-width: 2px;
}
.opstree .label {
    fill: black !important;
}
.opstree .h-connector {
    stroke-width: 0.1px;
    stroke-dasharray: 3 3;
}
.opstree .rejected {
    opacity: 0.25;
}
.opstree .level {
    opacity: 0.25;
}
.opstree .orange {
    fill: orange;
}
.tableline {
    fill: gray;
    opacity: 0.0;
}
.tableline:hover {
    opacity: 0.2;
}
.opstree .left.label g.shift {
    transform: translateX(-6px);
}
.opstree .right.label g.shift {
    transform: translateX(+6px);
}
.opstree .infobox text {
    text-anchor: start;
}
.opstree .shade {
    stroke: none;
}

.movetree .label .shift {
    transform: translateX(-18px);
}

.movetree .label text {
    text-anchor: end;
}
.movetree .v-connector {
    stroke: black;
}
.movetree .v-hook {
    stroke: black;
}
.movetree .ensembles .head .shift {
    transform: translateY(0px) rotate(270deg) ;
}
.movetree .ensembles .head text {
    text-anchor: start;
}
.movetree .connector.input {
    fill: green;
}
.movetree .connector.output {
    fill: red;
}
.movetree .unknown {
    fill: gray;
}
"""

# css_file = os.path.join(os.path.dirname(__file__), 'vis.css')
#
# with open(css_file, 'r') as content_file:
#     vis_css = content_file.read()
