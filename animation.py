# JAW
# frame1
# x=120, y=172, a=0.0
# frame2
# x=115, y=174, a=0.4
# frame3
# x=120, y=172, a=0.0
from math import floor

class keyFrame():
    def __init__(self,x,y,angle,label):
        self.x=x
        self.y=y
        self.angle=angle
        self.label=label

class animation():
    def __init__(self,keyFrames,duration,label):
        self.keyFrames=keyFrames
        self.duration=duration
        self.label=label
        self.frames=[]
    def calc_frames(self):
        for k in range(len(self.keyFrames)-1):
            for f in range(self.duration):
                frameX=(self.keyFrames[k].x-self.keyFrames[k+1].x)/self.duration
                frameY=(self.keyFrames[k].y-self.keyFrames[k+1].y)/self.duration
                frameAngle=(self.keyFrames[k].angle-self.keyFrames[k+1].angle)/self.duration
                self.frames.append({"x":-frameX,"y":-frameY,"angle":round(-frameAngle,4)})
        
if(__name__ == "__main__"):
    jawAnimation=animation([keyFrame(120,172,0.0,"frame1"),keyFrame(115,174,0.4,"frame2"),keyFrame(120,172,0.0,"frame3")],5,"jawAnimation")
    jawAnimation.calc_frames()
    raisingArmParent=animation([keyFrame(144,189,1.14,"frame1"),keyFrame(144,189,0.0,"frame2")],15,"raisingArmParent")
    raisingArmParent.calc_frames()
    raisingElbow=animation([keyFrame(144,189,0.0,"frame1"),keyFrame(144,189,-2.0,"frame2")],15,"raisingElbow")
    raisingElbow.calc_frames()
    raisingElbow=animation([keyFrame(144,189,-2.0,"frame1"),keyFrame(144,189,-1.0,"frame2"),keyFrame(144,189,-2.0,"frame3")],10,"waving")
    raisingElbow.calc_frames()
    
    animationsList=[jawAnimation,raisingArmParent,raisingElbow]
    
    with open("animations.txt","w") as f:
        for anim in animationsList:
            f.write(f"const Frame {anim.label}Frames[{anim.duration*(len(anim.keyFrames)-1)}]={{\n")
            x=0.0
            y=0.0
            for frame in anim.frames:
                x+=frame["x"]
                y+=frame["y"]
                f.write(f"{{.x={int(x)},.y={int(y)},.angle={frame['angle']}f}},\n")
                if(x>=1.0):x-=1.0
                elif(x<=-1.0):x+=1.0
                if(y>=1.0):y-=1.0
                elif(y<=-1.0):y+=1.0
            f.write("};\n")
