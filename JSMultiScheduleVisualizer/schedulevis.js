/**
 * Created by a.schnabel on 26.09.2016.
 */

class Vec2 {
    constructor(x, y) {
        this.x = x;
        this.y = y;
    }
}

class Rectangle {
    constructor(x, y, w, h) {
        this.x = x;
        this.y = y;
        this.w = w;
        this.h = h;
    }

    containsPoint(point) {
        return point.x >= this.x && point.x <= this.x + this.w && point.y >= this.y && point.y <= this.y + this.h;
    }
}

class Drawing {
    static drawRect(paper, rect, text, fontSize, fillcolor = '#ff0', bordercolor = '#000', textcolor = '#000') {
        const rectangle = paper.rect(rect.x, rect.y - rect.h, rect.w, rect.h).attr('fill', fillcolor).attr('stroke', bordercolor);
        const centerPos = new Vec2(rect.x + rect.w / 2.0, rect.y - rect.h / 2.0);
        const txt = paper.text(centerPos.x, centerPos.y, text).attr('font-size', fontSize).attr('fill', textcolor);
        return [rectangle, txt];
    }

    static drawLine(paper, base, offset) {
        const pth = paper.path('M' + base.x + ',' + base.y + 'L' + (base.x + offset.x) + ',' + (base.y + offset.y));
        pth.attr('stroke', '#000');
        pth.attr('stroke-width', 2);
        return pth;
    }

    static drawArrow(paper, base, offset) {
        return Drawing.drawLine(paper, base, offset).attr('arrow-end', 'classic-wide-long');
    }
}

class Helpers {
    static fill2(s) {
        if (s.length === 1) return '0' + s; else return s;
    }

    static rgb2hex(r,g,b) {
        return '#' + Helpers.fill2(r.toString(16)) + Helpers.fill2(g.toString(16)) + Helpers.fill2(b.toString(16));
    }

    static randomRGB(ub) {
        const r = parseInt(Math.random() * 255);
        const g = parseInt(Math.random() * 255);
        const b = parseInt(Math.random() * 255);
        return [r,g,b];
    }

    static brightnessFromRGB(r,g,b) {
        return (r + g + b) / (3.0 * 255.0);
    }

    static brightenRGB(r,g,b,incstep) {
        return [r,g,b].map(val => Math.min(val + incstep, 255));
    }

    static randomColors() {
        const genPair = function () {
            const [r,g,b] = Helpers.randomRGB(255);
            return [Helpers.brightnessFromRGB(r,g,b), Helpers.rgb2hex(r,g,b)];
        };

        const pair = genPair();
        const textcolor = pair[0] < 0.5 ? '#fff' : '#000';

        return {'textcolor': textcolor, 'rectcolor': pair[1]};
    }

    static batchGet(filenames, processPayloads) {
        const getRecursive = function (fns, payloads) {
            if (fns.length <= 0) {
                processPayloads.apply(this, payloads);
            } else {
                jQuery.get(fns[0], function (contents) {
                    const npayloads = payloads.slice(0);
                    npayloads.push(contents);
                    getRecursive(fns.slice(1), npayloads);
                });
            }
        };
        getRecursive(filenames, []);
    }
}

class ScheduleData {
    constructor(projects, schedules, solvetime, palette) {
        this.solvetime = solvetime;

        Math.seedrandom('99');

        this.projects = projects;
        this.schedules = schedules;

        let firstProject = projects[0];

        this.numProjects = projects.length;
        this.numJobs = firstProject.durations.length;
        this.numRes = 1;// firstProject.capacities.length;
        this.numPeriods = this.getMakespan() + 2;

        this.capacities = firstProject.capacities.slice(0,1);

        this.basicAssertions();

        this.scale = 35.0;
        this.origin = new Vec2(100, this.targetHeight() - 75);
        this.fontSize = 14;

        this.selectedResource = 0;

        this.recomputeRects = true;

        this.overlayObjects = [];
        for(let l=0; l<this.numProjects; l++) {
            this.overlayObjects.push({});
        }

        this.initJobColors(palette);
    }

    initJobColors(palette) {
        const incstep = 10;
        this.rcolors = [];
        for(let l=0; l<this.numProjects; l++) {
            this.rcolors.push([]);
            for(let j=0; j<this.numJobs; j++) {
                this.rcolors[l].push({
                    'rectcolor': palette[l][j+1].jobColor,
                    'textcolor': palette[l][j+1].textColor
                });
            }
        }
    }

    basicAssertions() {
        console.assert(this.numJobs === this.projects[0].demands[0].length);
        console.assert(this.numRes === this.projects[0].demands.length);
        for(let key in Object.keys(this.schedules))
            console.assert(this.numJobs === Object.keys(this.schedules[key]).length);
    }

    getDemand(l, j, r) {
        return this.projects[l].demands[r][j];
    }

    ft(l, j) {
        return this.schedules[l][j+1] + this.projects[l].durations[j];
    }

    static jobTitle(l, j) {
        return ''+(l+1)+':'+(j + 1);
    }

    drawQuad(paper, l, j, rcolors, xOffset, yOffset) {
        const rgeometry = new Rectangle(this.origin.x + xOffset, this.origin.y + yOffset, this.scale, this.scale);
        Drawing.drawRect(paper, rgeometry, ScheduleData.jobTitle(l,j), this.fontSize, rcolors.rectcolor, '#000', rcolors.textcolor);
        if (this.recomputeRects) {
            this.jobRects[l][j].push(new Rectangle(rgeometry.x, rgeometry.y - rgeometry.h, rgeometry.w, rgeometry.h));
        }
    }

    drawAxes(paper) {
        Drawing.drawArrow(paper, this.origin, new Vec2((this.numPeriods + 1) * this.scale, 0));
        paper.text(this.origin.x + (this.numPeriods + 2) * this.scale, this.origin.y, 'Time').attr('font-size', this.fontSize);
        for (let t = 0; t <= this.numPeriods; t++) {
            Drawing.drawLine(paper, new Vec2(this.origin.x + t * this.scale, this.origin.y), new Vec2(0, this.scale));
            if (t < this.numPeriods) {
                let boxCenter = new Vec2(this.origin.x + (t + 0.5) * this.scale, this.origin.y + this.scale * 0.5);
                paper.text(boxCenter.x, boxCenter.y, (t + 1)).attr('font-size', this.fontSize);
            }
        }

        //const capr = this.capacities[this.selectedResource];
        const capr = this.capacities[0];

        Drawing.drawArrow(paper, this.origin, new Vec2(0, -(capr + 1) * this.scale));
        paper.text(this.origin.x, this.origin.y - (capr + 1.5) * this.scale, 'Resource ' + (this.selectedResource + 1)).attr('font-size', this.fontSize);

        for (let k = 0; k <= capr; k++) {
            Drawing.drawLine(paper, new Vec2(this.origin.x - this.scale, this.origin.y - this.scale * k), new Vec2(this.scale, 0));
            if (k < capr) {
                let boxCenter = new Vec2(this.origin.x - 0.5 * this.scale, this.origin.y - this.scale * (k + 0.5));
                paper.text(boxCenter.x, boxCenter.y, (k + 1)).attr('font-size', this.fontSize);
            }
        }
        paper.text(this.origin.x - this.scale * 1.5, this.origin.y - this.scale * capr, 'Kr').attr('font-size', this.fontSize);

        Drawing.drawLine(paper, new Vec2(this.origin.x, this.origin.y - capr * this.scale), new Vec2((this.numPeriods + 1) * this.scale, 0)).attr('stroke', 'red').attr('stroke-dasharray', '--');
    }

    resetJobRectangles() {
        this.jobRects = [];
        for (let l = 0; l < this.numProjects; l++) {
            let lJobRects = [];
            this.jobRects.push(lJobRects);
            for (let j = 0; j < this.numJobs; j++) {
                lJobRects.push([])
            }
        }
    }

    drawDeadlines(paper) {
        const capr = this.capacities[0];
        for(let l = 0; l<this.numProjects; l++) {
            const xcoord = this.origin.x + this.projects[l].deadline*this.scale;
            const strokeColor = this.rcolors[l][0].rectcolor;
            Drawing.drawLine(paper, new Vec2(xcoord, this.origin.y), new Vec2(0, -(capr + 1) * this.scale)).attr('stroke', strokeColor).attr('stroke-dasharray', '--');
            paper.text(xcoord, this.origin.y - (capr + 1.5) * this.scale, 'd' + (l+1)).attr('font-size', this.fontSize);
        }
    }

    draw(paper, attrs) {
        this.drawAxes(paper);

        if (this.recomputeRects) this.resetJobRectangles();

        for (let t = 1; t <= this.numPeriods; t++) {
            let yOffset = 0;
            const xOffset = (t - 1) * this.scale;
            for (let l = 0; l < this.numProjects; l++) {
                for (let j = 0; j < this.numJobs; j++) {
                    if (this.schedules[l][j+1] >= 0 && this.schedules[l][j+1] < t && t <= this.ft(l, j)) {
                        for (let c = 0; c < this.getDemand(l, j, this.selectedResource); c++) {
                            this.drawQuad(paper, l, j, this.rcolors[l][j], xOffset, yOffset);
                            yOffset -= this.scale;
                        }
                    }
                }
            }
        }

        if (this.greyRect === undefined)
            this.greyRect = paper.rect(0, 0, this.targetWidth(), this.targetHeight()).attr('fill', '#eee').attr('opacity', 0.5);

        this.recomputeRects = false;

        this.drawDeadlines(paper);
    }

    changeResource(nres) {
        if (nres === this.selectedResource)
            return false;

        this.selectedResource = nres;
        this.recomputeRects = true;
        return true;
    }

    getResourceOptionStr() {
        let outStr = '';
        for (let r = 0; r < this.numRes; r++) {
            outStr += '<option>Resource ' + (r + 1) + '</option>';
        }
        return outStr;
    }

    targetHeight() {
        return this.scale * (Math.max(...this.capacities) + 4);
    }

    targetWidth() {
        return this.scale * (this.getMakespan() + 10);
    }

    getMakespan(l=-1) {
        if(l === -1) return Math.max(...[0,1,2].map(ix => this.getMakespan(ix)));
        return this.schedules[l][this.numJobs];
    }

    getDelayCosts(l=-1) {
        if(l === -1) return [0,1,2].reduce((acc,ix) => this.getDelayCosts(ix) + acc, 0);
        return Math.max(this.getMakespan(l) - this.projects[l].deadline, 0) * this.projects[l].delaycost;
    }

    checkJobHovering(pos) {
        for (let l = 0; l< this.numProjects; l++) {
            for (let j = 0; j < this.numJobs; j++) {
                for (let rect of this.jobRects[l][j]) {
                    if (rect.containsPoint(pos)) {
                        return {'projectIndex': l,  'jobIndex': j};
                    }
                }
            }
        }
        return undefined;
    }

    getJobOverlay(paper, pos, l, jobId, opacityLevel = 0.95) {
        if (this.overlayObjects[l][jobId] === undefined) {
            const dj = this.projects[l].durations[jobId];
            const r = new Rectangle(pos.x, pos.y, dj * this.scale, this.getDemand(l, jobId, this.selectedResource) * this.scale);
            const pair = Drawing.drawRect(paper, r, ScheduleData.jobTitle(l, jobId), this.fontSize, this.rcolors[l][jobId].rectcolor, '#000', this.rcolors[l][jobId].textcolor);
            pair[0].attr('opacity', opacityLevel);
            pair[1].attr('opacity', opacityLevel);
            const retObj = {};
            retObj.arrow1 = Drawing.drawArrow(paper, new Vec2(r.x, r.y + 10), new Vec2(r.w, 0)).attr('opacity', opacityLevel);
            retObj.arrow2 = Drawing.drawArrow(paper, new Vec2(r.x - 10, r.y), new Vec2(0, -r.h)).attr('opacity', opacityLevel);
            retObj.demandText = paper.text(r.x - 30, r.y - r.h / 2, 'k' + (jobId + 1) + '=' + this.getDemand(l, jobId, this.selectedResource)).attr('font-size', 15).attr('opacity', opacityLevel);
            retObj.durationText = paper.text(r.x + r.w / 2, r.y + 30, 'd' + (jobId + 1) + '=' + dj).attr('font-size', 15).attr('opacity', opacityLevel);
            retObj.rectangle = pair[0];
            retObj.rectGlow = retObj.rectangle.glow({'width': 5});
            retObj.text = pair[1];
            retObj.lastpos = pos;
            this.overlayObjects[l][jobId] = retObj;
            return retObj;
        } else {
            return this.overlayObjects[l][jobId];
        }

    }

    static moveJobOverlay(overlayObj, x, y) {
        const dx = x - overlayObj.lastpos.x;
        const dy = y - overlayObj.lastpos.y;
        for (let k in overlayObj) {
            if (k === 'lastpos') continue;
            overlayObj[k].translate(dx, dy);
        }
        overlayObj.lastpos.x = x;
        overlayObj.lastpos.y = y;
    }

    getExecutedActivitiesStr(l, invert = false) {
        const op = x => invert ? !x : x;
        let eas = '';
        for (let j = 0; j < this.numJobs; j++)
            if (op(this.schedules[l][j+1] !== -1))
                eas += (j + 1) + ', ';
        return eas.substring(0, eas.length - 2);
    }

    getNotExecutedActivitiesStr(l) {
        return this.getExecutedActivitiesStr(l, true);
    }

    hideOverlays() {
        for(let l=0; l<this.numProjects; l++) {
            for (let j=0; j<this.numJobs; j++) {
                for (let k in this.overlayObjects[l][j]) {
                    if (k === 'lastpos') continue;
                    this.overlayObjects[l][j][k].hide();
                }
            }
        }
        this.greyRect.hide();
    }

    showOverlay(paper, o) {
        this.greyRect.show();
        for (let k in o) {
            if (k === 'lastpos') continue;
            o[k].show();
        }
    }

    updateAttributesStr(paper, attrs) {
        const capr = this.capacities[this.selectedResource];
        let attrStr = '';
        for (let key in attrs.data) {
            if (key === 'executedActivities' || key === 'notExecutedActivities') continue;
            attrStr += key + '=' + attrs.data[key] + ', ';
        }
        attrStr = attrStr.substr(0, attrStr.length - 2);
        paper.text(this.origin.x + 600, this.origin.y - (capr + 1.5) * this.scale, attrStr).attr('font-size', 15);
    }
}

class Attributes {
    constructor(sd) {
        this.sd = sd;
        this.data = {
            'makespan': 0,
            'delayCosts': 0.0,
            'deadline': 0,
            'executedActivities': '...',
            'notExecutedActivities': '...'
        };
    }

    forProject(l) {
        const attrs = this.data;
        attrs.makespan = this.sd.getMakespan(l);
        attrs.delayCosts = this.sd.getDelayCosts(l);
        attrs.executedActivities = this.sd.getExecutedActivitiesStr(l);
        attrs.notExecutedActivities = this.sd.getNotExecutedActivitiesStr(l);
        attrs.deadline = this.sd.projects[l].deadline;
    }

    fillTable(l) {
        const attrs = this.data;
        this.forProject(l);
        $('#makespan' + (l+1)).html(attrs.makespan);
        $('#delay-costs' + (l+1)).html(attrs.delayCosts);
        $('#executed' + (l+1)).html(attrs.executedActivities);
        $('#not-executed' + (l+1)).html(attrs.notExecutedActivities);
        $('#deadline' + (l+1)).html(attrs.deadline);
    }

    fillTables() {
        for(let l=0; l<this.sd.numProjects; l++) {
            this.fillTable(l);
        }
    }

    fillGlobals() {
        $('#totalmakespan').html(this.sd.getMakespan());
        $('#totaldelaycosts').html(this.sd.getDelayCosts());
        $('#solvetime').html(this.sd.solvetime + ' s');
    }
}

const main = function (projects, schedulesObj, solvetime, palette) {
    const sd = new ScheduleData(projects, schedulesObj, solvetime, palette);
    const paper = Raphael(document.getElementById('area'), sd.targetWidth(), sd.targetHeight());

    const attrs = new Attributes(sd);

    sd.draw(paper, attrs);
    attrs.fillTables();
    attrs.fillGlobals();

    /*$('#resource-select').html(sd.getResourceOptionStr()).change(function () {
        if (sd.changeResource(parseInt($('#resource-select').val().replace('Resource ', '')) - 1))
            sd.draw(paper);
    });*/

    let hoverBefore = true;
    $('#area').mousemove(function (event) {
        const offset = $(this).offset();
        const mousePos = new Vec2(event.pageX - offset.left, event.pageY - offset.top);
        const hoveringOverJob = sd.checkJobHovering(mousePos);
        if (hoveringOverJob !== undefined) {
            const o = sd.getJobOverlay(paper, mousePos, hoveringOverJob.projectIndex, hoveringOverJob.jobIndex);
            sd.hideOverlays();
            sd.showOverlay(paper, o);
            ScheduleData.moveJobOverlay(o, mousePos.x, mousePos.y);
            hoverBefore = true;
        } else if (hoverBefore) {
            hoverBefore = false;
            sd.hideOverlays();
        }
    }).mouseleave(function (event) {
        sd.hideOverlays();
    });

    return sd;
};

const runAfterLoad = function (p1, p2, p3, ergebnisse, solvetime, jobcolors) {
    const sd = main([p1, p2, p3], ergebnisse, solvetime, jobcolors);

    const desiredPdfWidth = 400;
    const overlap = 20;

    for(let pix = 1; pix <= 3; pix++) {
        $('.overlayed' + pix).css('left', (desiredPdfWidth-overlap)*(pix-1));
        PDFJS.getDocument('forgviz' + pix + (window.location.search.substr(1) === 'sequential=1' ? 'Sequentiell' : '') + '.pdf').then(function (pdf) {
            pdf.getPage(1).then(function (page) {

                const viewport = page.getViewport(1);
                const scale = desiredPdfWidth / viewport.width;
                const scaledViewport = page.getViewport(scale);

                const canvas = document.getElementById('the-canvas' + pix);
                const context = canvas.getContext('2d');
                canvas.height = scaledViewport.height;
                canvas.width = scaledViewport.width;

                const renderContext = {
                    canvasContext: context,
                    viewport: scaledViewport
                };
                page.render(renderContext);
            });
        });
    }

    sd.hideOverlays();
};

function generateConverter(func) {
    return function(...strs) {
        func.apply(this, strs.map(str => (typeof str === 'string') ? JSON.parse(str) : str))
    }
}

function setupDialogs() {
    const registerControlDialog = function() {
        $('#control-container').dialog({
            autoOpen: false,
            show: { effect: "fade", duration: 1000 },
            dialogClass: "no-close",
            width: 600,
            height: 'auto',
            draggable: false
        });
    };

    const dialogs = [
        { 'caption': 'Project structures', 'sel': '#structurescontainer', 'w': '1250', 'h': '630', 'pos': 'left top', 'hideOverflow': true },
        { 'caption': 'Schedule', 'sel': '#schedulescontainer', 'w': '100%', 'h': '350', 'pos': 'center bottom', 'hideOverflow': true },
        { 'caption': 'Global data', 'sel': '#globaldatacontainer', 'w': '600', 'h': 'auto', 'pos': 'right center', 'hideOverflow': true },
        { 'caption': 'Per project data', 'sel': '#perprojectdatacontainer', 'w': '600', 'h': 'auto', 'pos': 'right top', 'hideOverflow': true },
    ];

    function registerDialog(dialog) {
        $(dialog.sel).dialog({
            autoOpen: true,
            show: {
                effect: "fade",
                duration: 1000
            },
            hide: {
                effect: "fade",
                duration: 1000
            },
            position: { my: 'center', at: dialog.pos, of: window },
            dialogClass: "no-close",
            width: dialog.w,
            height: dialog.h,
            draggable: false
        });

        if(dialog.hideOverflow)
            $(dialog.sel).css('overflow', 'hidden');

        const btnId = 'show'+dialog.sel.slice(1);
        $('#showbuttons').append('<button id="'+btnId+'" class="btn btn-primary">'+dialog.caption+'</button>');
        $('#'+btnId).click(function(ev) {
            $(dialog.sel).dialog('open');
            return false;
        });
    }

    dialogs.forEach(registerDialog);
    registerControlDialog();
}

$(document).ready(function () {
    setupDialogs();
    let projectObjects = [1,2,3].map(k => 'Projekt' + k + '.json');

    const sequential = window.location.search.substr(1) === 'sequential=1';
    const resultsFn = sequential ? 'ergebnisseSequentiell.json' : 'ergebnisse.json';
    const solvetimeFn = sequential ? 'solvetimeSequentiell.txt' : 'solvetime.txt';

    Helpers.batchGet(projectObjects.concat([resultsFn, solvetimeFn, 'jobcolors.json']), generateConverter(runAfterLoad));
});