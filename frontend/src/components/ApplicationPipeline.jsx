import React, { useState, useEffect } from 'react';
import { DragDropContext, Droppable, Draggable } from 'react-beautiful-dnd';
import { pipelineService } from '../services/pipelineService';
import { applicationService } from '../services/applicationService';
import { FaUser, FaEllipsisV } from 'react-icons/fa';

const ApplicationPipeline = () => {
               const [pipeline, setPipeline] = useState(null);
               const [stages, setStages] = useState([]);
               const [loading, setLoading] = useState(true);

               useEffect(() => {
                              loadPipeline();
               }, []);

               const loadPipeline = async () => {
                              try {
                                             const activePipeline = await pipelineService.getActivePipeline();
                                             if (activePipeline) {
                                                            const boardData = await pipelineService.getPipelineBoard(activePipeline._id);
                                                            setPipeline(activePipeline);
                                                            setStages(boardData.columns);
                                             }
                              } catch (error) {
                                             console.error("Failed to load pipeline", error);
                              } finally {
                                             setLoading(false);
                              }
               };

               const onDragEnd = async (result) => {
                              const { source, destination, draggableId } = result;

                              if (!destination) return;
                              if (source.droppableId === destination.droppableId && source.index === destination.index) return;

                              // Optimistic UI Update
                              const sourceStage = stages.find(s => s.id === source.droppableId);
                              const destStage = stages.find(s => s.id === destination.droppableId);
                              const movedCandidate = sourceStage.candidates.find(c => c.id === draggableId);

                              // Remove from source
                              sourceStage.candidates.splice(source.index, 1);
                              // Add to destination
                              destStage.candidates.splice(destination.index, 0, movedCandidate);

                              setStages([...stages]); // Trigger render

                              // API Call
                              try {
                                             await applicationService.moveStage(movedCandidate.application_id, destStage.id);
                              } catch (error) {
                                             console.error("Failed to move candidate", error);
                                             loadPipeline(); // Revert on error
                              }
               };

               if (loading) return <div className="p-8 text-center">Loading Pipeline...</div>;
               if (!pipeline) return <div className="p-8 text-center">No active pipeline found.</div>;

               return (
                              <div className="h-full flex flex-col bg-gray-50 overflow-hidden">
                                             <div className="p-4 border-b bg-white shadow-sm flex justify-between items-center">
                                                            <h2 className="text-xl font-bold text-gray-800">{pipeline.name}</h2>
                                                            <div className="text-sm text-gray-500">Drag and drop candidates to move stages</div>
                                             </div>

                                             <div className="flex-1 overflow-x-auto p-4">
                                                            <DragDropContext onDragEnd={onDragEnd}>
                                                                           <div className="flex h-full gap-4">
                                                                                          {stages.map(stage => (
                                                                                                         <Droppable key={stage.id} droppableId={stage.id}>
                                                                                                                        {(provided) => (
                                                                                                                                       <div
                                                                                                                                                      ref={provided.innerRef}
                                                                                                                                                      {...provided.droppableProps}
                                                                                                                                                      className="w-80 flex-shrink-0 flex flex-col bg-gray-100 rounded-lg max-h-full"
                                                                                                                                       >
                                                                                                                                                      <div className="p-3 font-semibold text-gray-700 bg-gray-200 rounded-t-lg flex justify-between">
                                                                                                                                                                     <span>{stage.name}</span>
                                                                                                                                                                     <span className="bg-white px-2 rounded-full text-xs py-1 text-gray-600">
                                                                                                                                                                                    {stage.candidates.length}
                                                                                                                                                                     </span>
                                                                                                                                                      </div>

                                                                                                                                                      <div className="p-2 flex-1 overflow-y-auto">
                                                                                                                                                                     {stage.candidates.map((candidate, index) => (
                                                                                                                                                                                    <Draggable
                                                                                                                                                                                                   key={candidate.id}
                                                                                                                                                                                                   draggableId={candidate.id}
                                                                                                                                                                                                   index={index}
                                                                                                                                                                                    >
                                                                                                                                                                                                   {(provided) => (
                                                                                                                                                                                                                  <div
                                                                                                                                                                                                                                 ref={provided.innerRef}
                                                                                                                                                                                                                                 {...provided.draggableProps}
                                                                                                                                                                                                                                 {...provided.dragHandleProps}
                                                                                                                                                                                                                                 className="bg-white p-3 mb-2 rounded shadow-sm border border-gray-200 hover:shadow-md transition-shadow"
                                                                                                                                                                                                                  >
                                                                                                                                                                                                                                 <div className="flex justify-between items-start mb-2">
                                                                                                                                                                                                                                                <h4 className="font-semibold text-gray-800">{candidate.name}</h4>
                                                                                                                                                                                                                                                <button className="text-gray-400 hover:text-gray-600">
                                                                                                                                                                                                                                                               <FaEllipsisV size={12} />
                                                                                                                                                                                                                                                </button>
                                                                                                                                                                                                                                 </div>
                                                                                                                                                                                                                                 <div className="text-sm text-gray-600 mb-2">
                                                                                                                                                                                                                                                {candidate.role}
                                                                                                                                                                                                                                 </div>
                                                                                                                                                                                                                                 <div className="flex justify-between items-center mt-3">
                                                                                                                                                                                                                                                <div className="flex items-center text-xs text-gray-500">
                                                                                                                                                                                                                                                               <FaUser className="mr-1" />
                                                                                                                                                                                                                                                               {candidate.match_score}% Match
                                                                                                                                                                                                                                                </div>
                                                                                                                                                                                                                                                <div className="text-xs text-blue-600 font-medium">
                                                                                                                                                                                                                                                               View
                                                                                                                                                                                                                                                </div>
                                                                                                                                                                                                                                 </div>
                                                                                                                                                                                                                  </div>
                                                                                                                                                                                                   )}
                                                                                                                                                                                    </Draggable>
                                                                                                                                                                     ))}
                                                                                                                                                                     {provided.placeholder}
                                                                                                                                                      </div>
                                                                                                                                       </div>
                                                                                                                        )}
                                                                                                         </Droppable>
                                                                                          ))}
                                                                           </div>
                                                            </DragDropContext>
                                             </div>
                              </div>
               );
};

export default ApplicationPipeline;
