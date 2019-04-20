# copypasted minimal versions
import json
import torch
class StatefulTaskSetting(object):
    def iterate_a_s(self, *, xx, oo=None, taskstate):
        for a in self.iterate_y(xx=xx, oo=oo, yy_prefix=taskstate):
            yield (a, self.next_taskstate(xx=xx, a=a, taskstate=taskstate))
    def iterate_a(self, *, xx, oo=None, taskstate):
        for a, _ in self.iterate_a_s(xx=xx, oo=oo, taskstate=taskstate):
            yield a
    def iterate_aa(self, *, xx, oo=None):
        def _finish_prefix(aa_prefix, taskstate):
            for a, s in self.iterate_a_s(xx=xx, oo=oo, taskstate=taskstate):
                if a is None:
                    yield aa_prefix
                else:
                    yield from _finish_prefix(aa_prefix + (a,), s)
        yield from _finish_prefix(tuple(), self.initial_taskstate(xx=xx))
class IncrementalScoringModel(object):
    def __init__(self, task):
        self.task = task            
    def score_aa(self, *, xx, aa):
        taskstate = self.task.initial_taskstate(xx=xx)
        modelstate = self.initial_modelstate(xx=xx)
        sum_score = 0
        for a in aa:
            score, modelstate = self.score_a_s(xx=xx, a=a, taskstate=taskstate, modelstate=modelstate)
            taskstate = self.task.next_taskstate(xx=xx, a=a, taskstate=taskstate)
            sum_score += score
        return sum_score
class BeamDecisionAgent(torch.nn.Module):
    def __init__(self, model, beam_size=15):
        super().__init__()
        torch.nn.Module.__init__(self)
        self.model = model
        self.beam_size = beam_size
    def decision(self, *, xx, oo=None):
        loss, best_aa = self(xx=xx)
        return best_aa
    def forward(self, *, xx, aa=None):
        assert aa == None
        initial_taskstate = self.model.task.initial_taskstate(xx=xx)
        initial_modelstate = self.model.initial_modelstate(xx=xx)
        queue = [(0, initial_taskstate, initial_modelstate, tuple())]
        while True:
            next_queue = []
            for pscore, ptaskstate, pmodelstate, aa_prefix in queue:
                for a, ntaskstate in self.model.task.iterate_a_s(xx=xx, taskstate=ptaskstate):
                    if a is None:
                        continue
                    nscore, nmodelstate = self.model.score_a_s(xx=xx, a=a, taskstate=ptaskstate, modelstate=pmodelstate)
                    next_queue.append((nscore + pscore, ntaskstate, nmodelstate, aa_prefix + (a,)))
            if len(next_queue) == 0:
                break
            next_queue.sort(key=lambda x: -float(x[0]))
            queue = next_queue[:self.beam_size]
        n = torch.log_softmax(torch.stack([q[0] for q in queue]), 0)
        return -n[0], tuple(queue[0][-1])
def draw_tree(tree):
    """
    tree = {'a/0.5': {}, 'b/0.5': {'B/0.5': {}}, }
    """
    from uuid import uuid4
    tree_id = "tree_" + uuid4().hex

    drawcalls = []
    drawcalls.append('g.setNode("c", { label: "context" , shape: "circle" });')
    drawcalls.append('g.node("c").style = "fill: #7f7";')

    # Just do it recursively
    def _draw_subtree(subtree, prefix=''):
        for i, (label, subsubtree) in enumerate(subtree.items()):
            node_id = prefix+'_'+str(i)
            drawcalls.append('g.setNode("' + node_id + '", { label: "" , shape: "circle" });')
            drawcalls.append('g.setEdge("' + prefix + '", "' + node_id + '", { arrowhead: "vee", label: ' + json.dumps(label) + '});')
            _draw_subtree(subsubtree, node_id)

    _draw_subtree(tree, 'c')

    if len(drawcalls) > 1200:
        return "Tree too large to draw!"
    
    try:
        from google.colab.output._publish import javascript
        javascript(url="https://cdnjs.cloudflare.com/ajax/libs/d3/4.13.0/d3.js")
        javascript(url="https://cdnjs.cloudflare.com/ajax/libs/dagre-d3/0.6.1/dagre-d3.min.js")
        non_colab = ""
    except:
        non_colab = '''
            <script>
                require.config({
                    paths: {
                        "d3": "https://cdnjs.cloudflare.com/ajax/libs/d3/4.13.0/d3",
                        "dagreD3": "https://cdnjs.cloudflare.com/ajax/libs/dagre-d3/0.6.1/dagre-d3.min"
                    }
                });
                try {
                    requirejs(['d3', 'dagreD3'], function() {});
                } catch (e) {}
                try {
                    require(['d3', 'dagreD3'], function() {});
                } catch (e) {}
            </script>
            <!--script>
                (function() {if(typeof d3 == "undefined") {
                    var script = document.createElement("script");
                    script.type = "text/javascript";
                    script.src = "https://cdnjs.cloudflare.com/ajax/libs/d3/4.13.0/d3.js";
                    document.body.appendChild(script);
                    var script = document.createElement("script");
                    script.type = "text/javascript";
                    script.src = "https://cdnjs.cloudflare.com/ajax/libs/dagre-d3/0.6.1/dagre-d3.min.js";
                    document.body.appendChild(script);
                }})();
            </script-->
        '''

    return non_colab + '''
    <style>
        .node rect, .node circle, .node ellipse {
            stroke: #333;
            fill: #fff;
            stroke-width: 1px;
        }
        .edgePath path {
            stroke: #333;
            fill: #333;
            stroke-width: 1.5px;
        }
    </style>
    ''' + f'<center><svg width="850" height="600" id="{tree_id}"><g/></svg></center>' + '''
    <script>
        (function render_d3() {
    ''' + ('''
            //var d3, dagreD3;
            try {
                d3 = require('d3');
                dagreD3 = require('dagreD3');
            } catch (e) { setTimeout(render_d3, 50); return; } // requirejs is broken on external domains
    ''' if non_colab != "" else "") + '''
            var g = new dagreD3.graphlib.Graph().setGraph({ 'rankdir': 'LR' });
    ''' + "\n".join(drawcalls) + f'var svg = d3.select("#{tree_id}");' + '''
            var inner = svg.select("g");
            // Set up zoom support
            var zoom = d3.zoom().scaleExtent([0.3, 5]).on("zoom", function() {
                inner.attr("transform", d3.event.transform);
            });
            svg.call(zoom);
            // Create the renderer
            var render = new dagreD3.render();
            // Run the renderer. This is what draws the final graph.
            render(inner, g);
            // Center the graph
            var initialScale = 0.75;
            svg.call(zoom.transform, d3.zoomIdentity.translate((svg.attr("width") - g.graph().width * initialScale) / 2, 20).scale(initialScale));
            svg.attr('height', g.graph().height * initialScale + 50);
        })();
    </script>
    '''