/**
 * Created by a.schnabel on 26.09.2016.
 */

let ws = undefined;
let lastSelProjIndex = 0;

function getOptional(obj, key, def = undefined) {
    return key in obj ? obj[key] : def;
}

function range(ub) {
    return [...Array(ub).keys()]
}

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
        const txt = text.length > 0 ? paper.text(centerPos.x, centerPos.y, text).attr('font-size', fontSize).attr('fill', textcolor) : undefined;
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
        this.origin = new Vec2(80, this.targetHeight() - 75);
        this.fontSize = 14;

        this.selectedResource = 0;

        this.recomputeRects = true;

        this.overlayObjects = [];
        for(let l=0; l<this.numProjects; l++) {
            this.overlayObjects.push({});
        }

        this.initJobColors(palette);

        if(this.capacities[0] <= 5) {
            $('#schedulescontainer').css('overflow', 'hidden');
        }
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
        return this.schedules[l][j] + this.projects[l].durations[j];
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
        paper.text(this.origin.x + (this.numPeriods + 2) * this.scale, this.origin.y, 'Zeit').attr('font-size', this.fontSize);
        for (let t = 0; t <= this.numPeriods; t++) {
            Drawing.drawLine(paper, new Vec2(this.origin.x + t * this.scale, this.origin.y), new Vec2(0, this.scale));
            if (t < this.numPeriods) {
                let boxCenter = new Vec2(this.origin.x + (t + 0.5) * this.scale, this.origin.y + this.scale * 0.5);
                paper.text(boxCenter.x, boxCenter.y, (t + 1)).attr('font-size', this.fontSize);
            }
        }

        //const capr = this.capacities[this.selectedResource];
        const maxOvertime = Math.max(...getOptional(this.projects[0], 'zmax', [0]));
        const capregular = this.capacities[0];
        const capr = this.capacities[0] + maxOvertime;

        Drawing.drawArrow(paper, this.origin, new Vec2(0, -(capr + 1) * this.scale));
        paper.text(this.origin.x, this.origin.y - (capr + 1.5) * this.scale, 'Ressource ' + (this.selectedResource + 1)).attr('font-size', this.fontSize);

        for (let k = 0; k <= capr; k++) {
            Drawing.drawLine(paper, new Vec2(this.origin.x - this.scale, this.origin.y - this.scale * k), new Vec2(this.scale, 0));
            if (k < capr) {
                let boxCenter = new Vec2(this.origin.x - 0.5 * this.scale, this.origin.y - this.scale * (k + 0.5));
                paper.text(boxCenter.x, boxCenter.y, (k + 1)).attr('font-size', this.fontSize);
            }
        }
        paper.text(this.origin.x - this.scale * 1.5, this.origin.y - this.scale * capregular, 'Kr').attr('font-size', this.fontSize);
        paper.text(this.origin.x - this.scale * 1.8, this.origin.y - this.scale * capr, 'Kr+oc').attr('font-size', this.fontSize);
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

    drawMakespanVerticalLines(paper) {
        const maxOvertime = Math.max(...getOptional(this.projects[0], 'zmax', [0]));
        const capregular = this.capacities[0];
        const capr = this.capacities[0] + maxOvertime;
        for(let l = 0; l<this.numProjects; l++) {
            const xcoord = this.origin.x + this.getMakespan(l) * this.scale;
            const strokeColor = this.rcolors[l][0].rectcolor;
            Drawing.drawLine(paper, new Vec2(xcoord, this.origin.y), new Vec2(0, -(capr + 1) * this.scale)).attr('stroke', strokeColor).attr('stroke-dasharray', '--');
            paper.text(xcoord, this.origin.y - (capr + 1.5) * this.scale, 'ms' + (l+1)).attr('font-size', this.fontSize);
        }
    }

    drawDashedHorizontalMaxLines(paper, caps) {
        const maxOvertime = Math.max(...getOptional(this.projects[0], 'zmax', [0]));
        const capregular = this.capacities[0];
        const capr = this.capacities[0] + maxOvertime;
        Drawing.drawLine(paper, new Vec2(this.origin.x, this.origin.y - capregular * this.scale), new Vec2((this.numPeriods + 1) * this.scale, 0)).attr('stroke', 'red').attr('stroke-dasharray', '--');
        Drawing.drawLine(paper, new Vec2(this.origin.x, this.origin.y - capr * this.scale), new Vec2((this.numPeriods + 1) * this.scale, 0)).attr('stroke', 'red').attr('stroke-dasharray', '--');
    }

    draw(paper, attrs) {
        this.drawAxes(paper);

        if (this.recomputeRects) this.resetJobRectangles();

        for (let t = 1; t <= this.numPeriods; t++) {
            let yOffset = 0;
            const xOffset = (t - 1) * this.scale;
            for (let l = 0; l < this.numProjects; l++) {
                for (let j = 0; j < this.numJobs; j++) {
                    if (this.schedules[l][j] >= 0 && this.schedules[l][j] < t && t <= this.ft(l, j)) {
                        for (let c = 0; c < this.getDemand(l, j, this.selectedResource); c++) {
                            this.drawQuad(paper, l, j, this.rcolors[l][j], xOffset, yOffset);
                            if(-yOffset / this.scale >= this.capacities[0]) {
                                const rcolors = { rectcolor: 'red', textcolor: 'red' };
                                const rgeometry = new Rectangle(this.origin.x + xOffset, this.origin.y + yOffset, this.scale, this.scale);
                                const robj = Drawing.drawRect(paper, rgeometry, '', this.fontSize, rcolors.rectcolor, '#000', rcolors.textcolor)[0];
                                robj.attr({opacity:0.5});
                            }
                            yOffset -= this.scale;
                        }
                    }
                }
            }
        }

        this.drawDashedHorizontalMaxLines(paper);

        if (this.greyRect === undefined)
            this.greyRect = paper.rect(0, 0, this.targetWidth(), this.targetHeight()).attr('fill', '#eee').attr('opacity', 0.5);

        this.recomputeRects = false;

        //this.drawDeadlines(paper);
        this.drawMakespanVerticalLines(paper);
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
        const maxOvertime = Math.max(...getOptional(this.projects[0], 'zmax', [0]));
        return this.scale * (Math.max(...this.capacities) + maxOvertime + 4);
    }

    targetWidth() {
        return this.scale * (this.getMakespan() + 10);
    }

    getMakespan(l=-1) {
        if(l === -1) return Math.max(...[0,1,2].map(ix => this.getMakespan(ix)));
        return this.schedules[l][this.numJobs-1];
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
            if (op(this.schedules[l][j] !== -1))
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

    getJobCosts(l) {
        let costs = 0;
        for (let j = 0; j < this.numJobs; j++)
            if (this.schedules[l][j] !== -1)
                costs += this.projects[l].costs[j];
        return costs;
    }

    activeInPeriod(l, j, t, stj) {
        if(stj < 0.0) return false;
        const ftj = stj + this.projects[l].durations[j];
        return stj < t && t <= ftj;
    }

    getOvertimeCosts() {
        let costs = 0;
        for(let t=0; t<this.numPeriods; t++) {
            for(let r=0; r<this.numRes; r++) {
                let cumDemand = 0;
                for(let l=0; l<this.numProjects; l++) {
                    for (let j = 0; j < this.numJobs; j++) {
                        if (this.activeInPeriod(l, j, t, this.schedules[l][j])) {
                            cumDemand += this.projects[l].demands[r][j];
                        }
                    }
                }
                costs += Math.max(0, cumDemand - this.projects[0].capacities[r]) * this.projects[0].kappa[r];
            }
        }
        return costs;
    }

    computeRevenue(l) {
        const ms = this.getMakespan(l);
        const ql = this.getReachedQualityLevel(l);
        const rperiods = this.projects[l].revenue_periods;

        /*
        let revIndex = -1;
        if (ms <= rperiods[0]) { revIndex = 0; }
        else if (ms === rperiods[1]) { revIndex = 1; }
        else { revIndex = 2; }
        const revenue = this.projects[l].revenues[ql][revIndex];
        */

        if(ql === -1) return 0.0;

        const revArray = this.projects[l].revenues[ql];

        if(rperiods.includes(ms)) {
            return revArray[ms-Math.min(...rperiods)]
        } else if(ms < Math.min(...rperiods)) {
            return revArray[0] + (Math.min(...rperiods)-ms);
        } else {
            return revArray[revArray.length-1] + (Math.max(...rperiods)-ms);
        }
    }

    getProfit(l=-1) {
        if(l === -1) {
            let profit = 0.0;
            for(let l2=0; l2<this.numProjects; l2++) {
                profit += this.getProfit(l2);
            }
            return profit - this.getOvertimeCosts();
        } else {
            return this.computeRevenue(l) - this.getJobCosts(l);
        }
    }


    getReachedQualityLevel(l) {
        const attributeValues = this.getQualityValues(l);
        const numQualityLevels = this.projects[l].qlevel_requirement[0].length;

        let allAttributesQualifyForLevel = function(qlevel) {
            for (let attr = 0; attr < attributeValues.length; attr++) {
                if(attributeValues[attr] < this.projects[l].qlevel_requirement[attr][qlevel]) {
                    return false;
                }
            }
            return true;
        }.bind(this);

        for(let qlevel = 0; qlevel < numQualityLevels; qlevel++) {
            if(allAttributesQualifyForLevel(qlevel)) {
                return qlevel;
            }
        }

        return -1;
    }

    getQualityValues(l) {
        let attributeValues = this.projects[l].base_qualities.slice(0);
        for (let j = 0; j < this.numJobs; j++) {
            if (this.schedules[l][j] !== -1) {
                for(let attr = 0; attr < attributeValues.length; attr++)
                    attributeValues[attr] += this.projects[l].quality_improvements[j][attr];
            }
        }
        return attributeValues;
    }
}

const translations = {
    makespan: 'Dauer',
    executedActivities: 'Ausgeführt',
    notExecutedActivities: 'Nicht ausgeführt',
    costs: 'Kosten',
    profit: 'Gewinn',
    qlevelreached: 'Q-Level',
    qvalues: 'Q-Werte',
    overtimeCosts: 'Überstundenkosten',
    totalProfit: 'Gewinn (gesamt)',
    solvetime: 'Rechenzeit'
};

function sortedKeys(obj) {
    const itsKeys = [];
    for(let attrKey in obj) {
        itsKeys.push(attrKey);
    }
    itsKeys.sort(function(a,b) {
        const [ca,cb] = [translations[a][0], translations[b][0]];
        if(ca < cb) return -1;
        else if(ca === cb) return 0;
        else return 1;
    });
    return itsKeys;
}

function fillTableIntoDocument(headerRow, itsId, tbl) {
    const rows = [];
    for(let attrKey of sortedKeys(tbl)) {
        const contents = tbl[attrKey].map(v => "<td>"+v+"</td>");
        rows.push('<tr><td>'+translations[attrKey]+'</td>'+contents+'</tr>');
    }

    $(itsId).html('<tbody>'+headerRow+rows.join('\n')+'</tbody>');
}

class Attributes {
    constructor(sd) {
        this.sd = sd;
        this.data = {
            'makespan': 0,
            //'delayCosts': 0.0,
            //'deadline': 0,
            'executedActivities': '...',
            'notExecutedActivities': '...',
            'costs': 0.0,
            'profit': 0.0,
            'qlevelreached': 0,
            'qvalues': '0, 0'
        };
    }

    forProject(l) {
        const attrs = this.data;
        attrs.makespan = this.sd.getMakespan(l);
        //attrs.delayCosts = this.sd.getDelayCosts(l);
        //attrs.deadline = this.sd.projects[l].deadline;
        attrs.executedActivities = this.sd.getExecutedActivitiesStr(l);
        attrs.notExecutedActivities = this.sd.getNotExecutedActivitiesStr(l);
        attrs.costs = this.sd.getJobCosts(l);
        attrs.profit = this.sd.getProfit(l);
        attrs.qlevelreached = ['A', 'B', 'C'][this.sd.getReachedQualityLevel(l)];
        attrs.qvalues = this.sd.getQualityValues(l).join(', ');
    }

    fillTables() {
        const headerRow = '<tr><th>Attribut</th><th>Projekt 1</th><th>Projekt 2</th><th>Projekt 3</th></tr>\n';
        const tbl = {};

        for(let l=0; l<this.sd.numProjects; l++) {
            this.forProject(l);
            for (let attrKey in this.data) {
                if (attrKey in this.data) {
                    const v = this.data[attrKey];
                    if(attrKey in tbl)
                        tbl[attrKey].push(v);
                    else
                        tbl[attrKey] = [v];
                }
            }
        }

        fillTableIntoDocument(headerRow, '#attrtbl', tbl);
    }

    fillGlobals() {
        const obj = {
            'makespan': this.sd.getMakespan(),
            //'delayCosts': this.sd.getDelayCosts(),
            'overtimeCosts': this.sd.getOvertimeCosts(),
            'totalProfit': this.sd.getProfit(),
            'solvetime': this.sd.solvetime + ' s'
        };

        const headerRow = '<tr><th>Attribut</th><th>Wert</th></tr>\n';
        const tbl = {};

        for (let attrKey in obj) {
            if (attrKey in obj) {
                const v = obj[attrKey];
                tbl[attrKey] = [v];
            }
        }

        fillTableIntoDocument(headerRow, '#totaltbl', tbl);
    }
}

function columnDescriptorForProject(p) {

    function predListStrFromAdj(adj, j) {
        return p.jobs.filter(i => adj[i-1][j]).join(',');
    }

    function triggersListStr(trigger_adj, j) {
        return p.jobs.filter(k => trigger_adj[j][k-1]).join(',');
    }

    return {
        header: ['Ver-pflichtend', 'Dauer', 'Verbrauch<br />Erneuerbar', 'Verbrauch<br />Nicht-Erneuerbar', 'Kosten', 'Zuwachs 1', 'Zuwachs 2', 'Vorgänger', 'Bedingt'],
        labels: ['mandatory', 'duration', 'demand_r', 'demand_n', 'cost', 'qincr_1', 'qincr_2', 'preds', 'triggers'],
        types: ['bool', 'int', 'int', 'int', 'float', 'int', 'int', 'int list', 'int list'],
        valueFunc: function(j) {
            return [
                p.mandatory_activities.includes(j+1),
                p.durations[j],
                p.demands[0][j],
                p.demands_nonrenewable[0][j],
                p.costs[j],
                p.quality_improvements[j][0],
                p.quality_improvements[j][1],
                predListStrFromAdj(p.precedence, j),
                triggersListStr(p.job_causing_job, j)
            ];
        }
    };
}

function numInput(label, val) {
    return `<input class="num-input form-control" type="number" id="${label}" value="${val}" />`;
}

function generateActivityInputTableHtml(projects, l) {

    function infield_col(label, itype, val) {
        let [prefix, infix, suffix] = ['<td>', '', '</td>'];
        if(itype === 'int' || itype === 'float') {
            infix = numInput(label, val);
        } else if(itype === 'bool') {
            infix = '<input type="checkbox" id="'+label+'" '+(val ? 'checked' : '')+'/>';
        } else if(itype === 'int list') {
            infix = '<input class="wide-input form-control" type="text" id="'+label+'" value="'+val+'" />';
        }
        return prefix+infix+suffix;
    }

    const p = projects[l];

    const colDescr = columnDescriptorForProject(p);

    const headerRow = '<th>'+['AG'].concat(colDescr.header).join('</th><th>')+'</th>';

    const rows = [];

    for(let job of p.jobs) {
        let row = '<tr><td>'+job+'</td>';
        let j = job-1;
        for(let ix = 0; ix<colDescr.labels.length; ix++) {
            row += infield_col(colDescr.labels[ix]+'_'+j, colDescr.types[ix], colDescr.valueFunc(j)[ix]);
        }
        row += '</tr>';
        rows.push(row);
    }

    return '<table>' + headerRow + rows.join('\n') + '</table>';

}

function generateDecisionInputTableHtml(projects, l) {
    const headerRow = '<tr><th>Entscheidung</th><th>Auslöser AG</th><th>Jobs in Entscheidung</th></tr>';
    const rows = [];

    const p = projects[l];

    const ndecisions = p.job_in_decision[0].length;

    function causing_job_input(e) {
        const val = p.job_activating_decision.findIndex(function(tpl) {
            return tpl[e];
        }) + 1;
        return numInput(`job_causing_decision_${e}`, val);
    }

    function jobs_in_decision(e) {
        return p.jobs.filter(j=>p.job_in_decision[j-1][e]);
    }

    function jobs_in_dec_input(e) {
        return `<input class="wide-input form-control" type="text" id="jobs_in_decision_${e}" value="${jobs_in_decision(e).join(',')}" />`;
    }

    for(let e=0; e<ndecisions; e++) {
        rows.push(`<tr><td>${e+1}</td><td>${causing_job_input(e)}</td><td>${jobs_in_dec_input(e)}</td></tr>`);
    }

    return '<table>' + headerRow + rows.join('\n') + '</table>';
}

function generateGlobalInputTableHtml(projects, l) {
    const headerRow = '<tr><th>Ressource</th><th>Kap. Erneuerbar</th><th>Kap. Nicht-erneuerbar</th><th>Überstunden Limit</th><th>Überstunden Kostenfaktor</th></tr>';
    const rows = [];
    const p = projects[l];
    const nres = 1;

    for(let r=0; r<nres; r++) {
        rows.push(`<tr><td>${r+1}</td><td>${numInput('cap_renew_'+r, p.capacities[0])}</td><td>${numInput('cap_non_renew_'+r, p.capacities[1])}</td><td>${numInput('zmax_'+r, p.zmax[0])}</td><td>${numInput('kappa_'+r, p.kappa[0])}</td></tr>`);
    }

    return '<table>' + headerRow + rows.join('\n') + '</table>';
}

function generateQualityInputTableHtml(projects, l) {
    const headerRow = '<tr><th>Q-Attribut</th><th>A</th><th>B</th><th>C</th><th>Basis</th></tr>';
    const rows = [];
    const p = projects[l];
    const nattrs = p.base_qualities.length;

    for(let o=0; o<nattrs; o++) {
        const level_inputs = [];
        for(let level=0; level<3; level++) {
            level_inputs.push(numInput(`min_${o}_for_level_${level}`, p.qlevel_requirement[o][level]));
        }
        rows.push(`<tr><td>${o+1}</td><td>${level_inputs.join('</td><td>')}</td><td>${numInput('base_'+o, p.base_qualities[o])}</td></tr>`);
    }

    return '<table>' + headerRow + rows.join('\n') + '</table>';
}

function generateRevenueInputTableHtml(projects, l) {
    const headerRow = '<tr><th>Projektdauer</th><th>A</th><th>B</th><th>C</th></tr>';
    const rows = [];
    const p = projects[l];

    for(let t=0; t<p.revenue_periods.length; t++) {
        const level_revenue_inputs = [];
        for(let level=0; level<3; level++) {
            level_revenue_inputs.push(numInput(`revenue_${t}_${level}`, p.revenues[t][level]));
        }
        rows.push(`<tr><td>${p.revenue_periods[t]}</td><td>${level_revenue_inputs.join('</td><td>')}</td></tr>`);
    }

    return '<table>' + headerRow + rows.join('\n') + '</table>';
}

function fillProjectInputFieldsFromMemory(projects, l) {
    const colDescr = columnDescriptorForProject(projects[l]);
    for(let job of projects[l].jobs) {
        let j = job-1;
        for(let ix = 0; ix<colDescr.labels.length; ix++) {
            const itsId = '#'+colDescr.labels[ix] + '_' + j;
            const it = colDescr.types[ix];
            const itsVal = colDescr.valueFunc(j)[ix];
            if(it === 'int' || it === 'float' || it === 'int list') {
                $(itsId).val(itsVal);
            } else if(it === 'bool') {
                $(itsId).prop('checked', itsVal);
            }
        }
    }

    const p = projects[l];

    $(`#job_causing_decision_0`).val(p.job_activating_decision.findIndex(function(tpl) {
        return tpl[0];
    })+1);
    $(`#jobs_in_decision_0`).val(p.jobs.filter(j=>p.job_in_decision[j-1][0]).join(','));

    const nattrs = p.qlevel_requirement.length;
    const nlevels = p.qlevel_requirement[0].length;

    for(let o=0; o<nattrs; o++) {
        for (let level = 0; level < nlevels; level++) {
            $(`#min_${o}_for_level_${level}`).val(p.qlevel_requirement[o][level]);
        }
        $(`#base_${o}`).val(p.base_qualities[o]);
    }

    for(let t=0; t<p.revenue_periods.length; t++) {
        const level_revenue_inputs = [];
        for(let level=0; level<3; level++) {
            $(`#revenue_${t}_${level}`).val(p.revenues[t][level]);
        }
    }
}

function updateProjectFromInput(p) {
    function assignFromIdsWithPrefix(outKey, prefix, nested = false, isfloat = false) {
        const cast = isfloat ? parseFloat : parseInt;
        const v = p.jobs.map(j => cast($(`#${prefix}_${j-1}`).val()));
        p[outKey] = nested ? [v] : v;
    }

    p.mandatory_activities = p.jobs.filter(j => $(`#mandatory_${j-1}`).is(':checked'));

    assignFromIdsWithPrefix('durations', 'duration');
    assignFromIdsWithPrefix('demands', 'demand_r', true);
    assignFromIdsWithPrefix('demands_nonrenewable', 'demand_n', true);
    assignFromIdsWithPrefix('costs', 'cost', false, true);

    p.quality_improvements = p.jobs.map(j => [ parseInt($(`#qincr_1_${j-1}`).val()), parseInt($(`#qincr_2_${j-1}`).val()) ]);

    function ispred(i, j) {
        const c = $(`#preds_${j-1}`).val();
        return c.length > 0 && c.split(',').map(k => parseInt(k)).includes(i);
    }

    function iscausing(i, j) {
        const c = $(`#triggers_${i-1}`).val();
        return c.length > 0 && c.split(',').map(k => parseInt(k)).includes(j);
    }

    p.precedence = p.jobs.map(i => p.jobs.map(j => ispred(i,j)));
    p.job_causing_job = p.jobs.map(i => p.jobs.map(j => iscausing(i,j)));

    const a = e => parseInt($(`#job_causing_decision_${e}`).val());
    const decisions = [0];
    p.job_activating_decision = p.jobs.map(j =>  decisions.map(e => j === a(e)) );

    const jid = $(`#jobs_in_decision_0`).val().split(',').map(j => parseInt(j));
    p.job_in_decision = p.jobs.map(j => [jid.includes(j)]);

    const nattrs = p.base_qualities.length;
    const nlevels = p.qlevel_requirement[0].length;

    p.qlevel_requirement = range(nattrs).map(o => range(nlevels).map(level => parseInt($(`#min_${o}_for_level_${level}`).val())));
    p.base_qualities = range(nattrs).map(o => parseInt($(`#base_${o}`).val()));

    p.revenues = range(p.revenue_periods.length).map(t => range(nlevels).map(level => parseInt($(`#revenue_${t}_${level}`).val())));
}

function updateGlobalDataFromInput(projects) {
    for(let l=0; l<projects.length; l++) {
        projects[l].capacities = [ $('#cap_renew_0').val(), $('#cap_non_renew_0').val() ];
        projects[l].zmax = [ $('#zmax_0').val() ];
        projects[l].kappa = [ $('#kappa_0').val() ];
    }
}

/*function checkForModification(obj, operation) {
    const strBefore = JSON.stringify(obj);
    const strNow = JSON.stringify(operation());
    if(strNow !== strBefore) {
        console.assert(false);
    }
}*/

function setupInputDialog(projects) {
    $('#input-job-data').html(generateActivityInputTableHtml(projects, 0));
    $('#input-decision-data').html(generateDecisionInputTableHtml(projects, 0));
    $('#input-global-data').html(generateGlobalInputTableHtml(projects, 0));
    $('#input-quality-data').html(generateQualityInputTableHtml(projects, 0));
    $('#input-revenue-data').html(generateRevenueInputTableHtml(projects, 0));

    $('#project-select').change(function() {
        const selProjIndex = parseInt($('#project-select option:selected').val());
        updateProjectFromInput(projects[lastSelProjIndex]);
        fillProjectInputFieldsFromMemory(projects, selProjIndex);
        lastSelProjIndex = selProjIndex;
    });
}

const main = function (projects, schedulesObj, solvetime, palette) {
    setupInputDialog(projects);

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

    for(let pix = 1; pix <= 3; pix++) {
        const pdfFilename = 'forgviz' + pix + (window.location.search.substr(1) === 'sequential=1' ? 'Sequentiell' : '') + '.pdf';
        PDFJS.getDocument(pdfFilename).then(function (pdf) {
            pdf.getPage(1).then(function (page) {

                const viewport = page.getViewport(1);
                const desiredPdfHeight = 580;
                const scale = desiredPdfHeight / viewport.height;
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

    $('#optimizeBtn').click(function() {
        const selProjIndex = parseInt($('#project-select option:selected').val());
        updateProjectFromInput(sd.projects[selProjIndex]);
        console.log('Sending data for optimization...');
        console.log(sd.projects);
        ws.send(JSON.stringify({type: 'optimize', payload: sd.projects}));
    });

    $('#resetBtn').click(function() {
        ws.send(JSON.stringify({type: 'reset_from_excel'}));
    });
};

function generateConverter(func) {
    return function(...strs) {
        func.apply(this, strs.map(str => (typeof str === 'string') ? JSON.parse(str) : str))
    }
}

function setupDialogs() {
    const registerControlDialog = function() {
        $('#control-container').dialog({
            autoOpen: true,
            show: {
                effect: "fade",
                duration: 1000
            },
            hide: {
                effect: "fade",
                duration: 1000
            },
            dialogClass: "no-close",
            width: 600,
            height: 'auto',
			draggable: true
        });
    };

    const dialogs = [
        { caption: 'Projektstrukturen', sel: '#structurescontainer', w: '1300', h: '630', pos: 'left top', hideOverflow: true },
        { caption: 'Ablaufplan', sel: '#schedulescontainer', w: 'auto', h: '400', pos: 'left bottom', hideOverflow: false },
        { caption: 'Resultate', sel: '#globaldatacontainer', w: '400', h: 'auto', pos: 'right center', hideOverflow: true },
        { caption: 'Projektresultate', sel: '#perprojectdatacontainer', w: '600', h: 'auto', pos: 'right top', hideOverflow: true },
        { caption: 'Eingabe', sel: '#input-container', w: 'auto', h: 'auto', pos: 'center top', hideOverflow: false },
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
            draggable: true
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

    $('#progress-container').dialog({
        autoOpen: false,
        show: {
            effect: "fade",
            duration: 1000
        },
        hide: {
            effect: "fade",
            duration: 1000
        },
        position: { my: 'center', at: 'center', of: window },
        dialogClass: "no-close",
        width: 'auto',
        height: 'auto',
        draggable: true
    });
}

$(document).ready(function () {
    $('#showIntegratedResults').click(function(){
        window.location.href = "http://localhost:8000/schedulevis.html?sequential=0";
    });
    $('#showSequentialResults').click(function(){
        window.location.href = "http://localhost:8000/schedulevis.html?sequential=1";
    });

    ws = new WebSocket("ws://127.0.0.1:5678/");

    setupDialogs();
    let projectObjects = [1,2,3].map(k => 'Projekt' + k + '.json');

    const sequential = window.location.search.substr(1) === 'sequential=1';
    const resultsFn = sequential ? 'ergebnisseSequentiell.json' : 'ergebnisse.json';
    const solvetimeFn = sequential ? 'solvetimeSequentiell.txt' : 'solvetime.txt';

    Helpers.batchGet(projectObjects.concat([resultsFn, solvetimeFn, 'jobcolors.json']), generateConverter(runAfterLoad));

    ws.onmessage = function (event) {
        const msg = event.data;
        if(msg === 'finished') {
            location.reload();
        } else if(msg === 'started') {
            $('#progress-container').dialog('open');
        }
    };
});