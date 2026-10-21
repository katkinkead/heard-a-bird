let liveMarks=[];
    function prepareLiveMarks(){
      refCtx.clearRect(0,0,W,H);refCtx.drawImage(images.robin,0,0,W,H);
      liveMarks=buildSpeciesFinish({pixels:refCtx.getImageData(0,0,W,H).data,width:W,height:H,config:{
        birdPoly:[],extrasBoxes:[],backgroundBoxes:[],focalBoxes:[],
        textBoxes:[{box:[905,695,991,720],limit:158,start:88.2,end:89.7,label:'Singing now'},
          {box:[925,675,972,697],limit:189,start:87.8,end:88.8,label:'Live ripple'}]
      }});
    }